"""
Management command to generate HLS/DASH streams for videos.
"""
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.videos.models import Video, VideoStream
from apps.videos.services.hls_service import HLSService
from apps.videos.services.dash_service import DASHService


class Command(BaseCommand):
    help = 'Generate HLS/DASH streams for videos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--video-id',
            type=int,
            help='Generate streams for specific video ID'
        )
        parser.add_argument(
            '--stream-type',
            type=str,
            choices=['hls', 'dash', 'both'],
            default='both',
            help='Type of stream to generate (hls, dash, or both)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Regenerate streams even if they already exist'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='Maximum number of videos to process'
        )

    def handle(self, *args, **options):
        video_id = options.get('video_id')
        stream_type = options.get('stream_type')
        force = options.get('force')
        limit = options.get('limit')
        
        self.stdout.write('🎬 Generating video streams...')
        self.stdout.write('=' * 50)
        
        # Get videos to process
        if video_id:
            videos = Video.objects.filter(id=video_id, status='published')
        else:
            videos = Video.objects.filter(
                status='published',
                processing_status='completed'
            ).exclude(
                temp_video_file__isnull=True
            ).exclude(
                temp_video_file=''
            )[:limit]
        
        if not videos.exists():
            self.stdout.write(self.style.WARNING('No videos found to process'))
            return
        
        self.stdout.write(f'Found {videos.count()} videos to process')
        self.stdout.write('')
        
        hls_service = HLSService()
        dash_service = DASHService()
        
        success_count = 0
        error_count = 0
        skipped_count = 0
        
        for video in videos:
            self.stdout.write(f'Processing: {video.title} (ID: {video.id})')
            
            # Check if video file exists
            video_path = None
            if video.temp_video_file:
                try:
                    video_path = video.temp_video_file.path
                    if not os.path.exists(video_path):
                        video_path = None
                except:
                    pass
            
            if not video_path:
                self.stdout.write(self.style.WARNING('  ✗ Video file not found, skipping'))
                skipped_count += 1
                continue
            
            # Check if streams already exist
            if not force:
                existing_streams = VideoStream.objects.filter(
                    video=video,
                    is_ready=True
                )
                if stream_type == 'both' and existing_streams.count() >= 2:
                    self.stdout.write(self.style.WARNING('  - Streams already exist, skipping'))
                    skipped_count += 1
                    continue
                elif stream_type != 'both' and existing_streams.filter(stream_type=stream_type).exists():
                    self.stdout.write(self.style.WARNING(f'  - {stream_type.upper()} stream already exists, skipping'))
                    skipped_count += 1
                    continue
            
            try:
                # Generate HLS
                if stream_type in ['hls', 'both']:
                    self.stdout.write('  → Generating HLS streams...')
                    hls_success = self._generate_hls(video, video_path, hls_service, force)
                    if hls_success:
                        self.stdout.write(self.style.SUCCESS('    ✓ HLS generated'))
                    else:
                        self.stdout.write(self.style.ERROR('    ✗ HLS failed'))
                
                # Generate DASH
                if stream_type in ['dash', 'both']:
                    self.stdout.write('  → Generating DASH streams...')
                    dash_success = self._generate_dash(video, video_path, dash_service, force)
                    if dash_success:
                        self.stdout.write(self.style.SUCCESS('    ✓ DASH generated'))
                    else:
                        self.stdout.write(self.style.ERROR('    ✗ DASH failed'))
                
                success_count += 1
                self.stdout.write(self.style.SUCCESS(f'  ✓ Completed'))
                
            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f'  ✗ Error: {str(e)}'))
            
            self.stdout.write('')
        
        # Summary
        self.stdout.write('=' * 50)
        self.stdout.write(self.style.SUCCESS(f'✓ Success: {success_count}'))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'✗ Errors: {error_count}'))
        if skipped_count > 0:
            self.stdout.write(self.style.WARNING(f'- Skipped: {skipped_count}'))
        self.stdout.write('')
        self.stdout.write('Done!')
    
    def _generate_hls(self, video, video_path, hls_service, force):
        """Generate HLS streams for video."""
        from apps.videos.models_encoding import VideoEncodingProfile
        
        # Get profiles
        profiles = VideoEncodingProfile.objects.filter(is_active=True).order_by('bitrate')
        
        if not profiles.exists():
            return False
        
        # Output directory
        output_base = os.path.join(settings.MEDIA_ROOT, 'streams', 'hls', str(video.id))
        os.makedirs(output_base, exist_ok=True)
        
        hls_outputs = []
        
        for profile in profiles:
            output_dir = os.path.join(output_base, f'{profile.resolution}p')
            
            # Skip if already exists and not forcing
            if not force and os.path.exists(os.path.join(output_dir, 'playlist.m3u8')):
                continue
            
            os.makedirs(output_dir, exist_ok=True)
            
            try:
                result = hls_service.generate(
                    video_path=video_path,
                    output_dir=output_dir,
                    profile_name=f'{profile.resolution}p',
                    width=profile.width,
                    height=profile.height,
                    bitrate=profile.bitrate
                )
                
                if result['success']:
                    hls_outputs.append(result)
                    
                    # Save to database
                    VideoStream.objects.update_or_create(
                        video=video,
                        stream_type='hls',
                        profile=profile,
                        defaults={
                            'manifest_path': result['playlist_path'],
                            'segment_count': result['segment_count'],
                            'total_size': result['total_size'],
                            'is_ready': True
                        }
                    )
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'    Warning: Failed to generate {profile.resolution}p: {e}'))
        
        # Generate master playlist
        if hls_outputs:
            master_path = os.path.join(output_base, 'master.m3u8')
            base_url = f'/media/streams/hls/{video.id}/'
            hls_service.generate_master_playlist(hls_outputs, master_path, base_url)
        
        return len(hls_outputs) > 0
    
    def _generate_dash(self, video, video_path, dash_service, force):
        """Generate DASH streams for video."""
        from apps.videos.models_encoding import VideoEncodingProfile
        
        # Get profiles
        profiles = VideoEncodingProfile.objects.filter(is_active=True).order_by('bitrate')
        
        if not profiles.exists():
            return False
        
        # Output directory
        output_base = os.path.join(settings.MEDIA_ROOT, 'streams', 'dash', str(video.id))
        os.makedirs(output_base, exist_ok=True)
        
        dash_outputs = []
        
        for profile in profiles:
            output_dir = os.path.join(output_base, f'{profile.resolution}p')
            
            # Skip if already exists and not forcing
            if not force and os.path.exists(os.path.join(output_dir, 'manifest.mpd')):
                continue
            
            os.makedirs(output_dir, exist_ok=True)
            
            try:
                result = dash_service.generate(
                    video_path=video_path,
                    output_dir=output_dir,
                    profile_name=f'{profile.resolution}p',
                    width=profile.width,
                    height=profile.height,
                    bitrate=profile.bitrate
                )
                
                if result['success']:
                    dash_outputs.append(result)
                    
                    # Save to database
                    VideoStream.objects.update_or_create(
                        video=video,
                        stream_type='dash',
                        profile=profile,
                        defaults={
                            'manifest_path': result['manifest_path'],
                            'segment_count': result['segment_count'],
                            'total_size': result['total_size'],
                            'is_ready': True
                        }
                    )
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'    Warning: Failed to generate {profile.resolution}p: {e}'))
        
        # Generate master MPD
        if dash_outputs:
            master_path = os.path.join(output_base, 'master.mpd')
            base_url = f'/media/streams/dash/{video.id}/'
            
            # Get video duration
            duration = video.duration if video.duration else 0
            
            dash_service.generate_master_mpd(dash_outputs, master_path, duration, base_url)
        
        return len(dash_outputs) > 0
