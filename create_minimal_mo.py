#!/usr/bin/env python3
"""
Create minimal .mo files that Django can read.
"""

import struct
import os

def create_minimal_mo(mo_path):
    """Create a minimal .mo file with just the header."""
    
    # Create minimal .mo file with just header
    # Magic number for .mo files
    output = struct.pack('<I', 0x950412de)  # Magic number
    output += struct.pack('<I', 0)          # Version
    output += struct.pack('<I', 0)          # Number of entries
    output += struct.pack('<I', 28)         # Offset of key table
    output += struct.pack('<I', 28)         # Offset of value table  
    output += struct.pack('<I', 0)          # Hash table size
    output += struct.pack('<I', 0)          # Hash table offset
    
    # Write .mo file
    with open(mo_path, 'wb') as f:
        f.write(output)
    
    print(f"Created minimal {mo_path}")

def main():
    """Main function."""
    
    # Create minimal .mo files
    create_minimal_mo('locale/ru/LC_MESSAGES/django.mo')
    create_minimal_mo('locale/en/LC_MESSAGES/django.mo')

if __name__ == '__main__':
    main()