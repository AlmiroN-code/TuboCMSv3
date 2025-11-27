#!/usr/bin/env python3
"""
Simple script to create basic .mo files without gettext tools.
This creates minimal .mo files that Django can read.
"""

import os
import struct

def create_mo_file(po_file_path, mo_file_path):
    """Create a basic .mo file from .po file."""
    
    # Read .po file and extract translations
    translations = {}
    
    try:
        with open(po_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Simple parsing of .po file
        lines = content.split('\n')
        msgid = None
        msgstr = None
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('msgid "') and line.endswith('"'):
                msgid = line[7:-1]  # Remove 'msgid "' and '"'
                
            elif line.startswith('msgstr "') and line.endswith('"'):
                msgstr = line[8:-1]  # Remove 'msgstr "' and '"'
                
                # Add translation if both msgid and msgstr exist and are not empty
                if msgid and msgstr and msgid != '' and msgstr != '':
                    translations[msgid] = msgstr
                    
                msgid = None
                msgstr = None
    
    except Exception as e:
        print(f"Error reading {po_file_path}: {e}")
        return False
    
    # Create .mo file
    try:
        # Create basic .mo file structure
        keys = list(translations.keys())
        values = list(translations.values())
        
        # Encode strings
        kencoded = [k.encode('utf-8') for k in keys]
        vencoded = [v.encode('utf-8') for v in values]
        
        # Create .mo file content
        keystart = 7 * 4 + 16 * len(keys)
        valuestart = keystart + sum(len(k) for k in kencoded)
        
        # Header
        output = struct.pack('<I', 0x950412de)  # Magic number
        output += struct.pack('<I', 0)          # Version
        output += struct.pack('<I', len(keys))  # Number of entries
        output += struct.pack('<I', 7 * 4)      # Offset of key table
        output += struct.pack('<I', 7 * 4 + 8 * len(keys))  # Offset of value table
        output += struct.pack('<I', 0)          # Hash table size
        output += struct.pack('<I', 0)          # Hash table offset
        
        # Key table
        koffsets = []
        voffsets = []
        
        # Calculate offsets
        koffset = keystart
        for k in kencoded:
            koffsets.append(koffset)
            koffset += len(k)
            
        voffset = valuestart
        for v in vencoded:
            voffsets.append(voffset)
            voffset += len(v)
        
        # Write key table
        for i in range(len(keys)):
            output += struct.pack('<I', len(kencoded[i]))
            output += struct.pack('<I', koffsets[i])
            
        # Write value table
        for i in range(len(values)):
            output += struct.pack('<I', len(vencoded[i]))
            output += struct.pack('<I', voffsets[i])
            
        # Write keys
        for k in kencoded:
            output += k
            
        # Write values
        for v in vencoded:
            output += v
        
        # Write .mo file
        with open(mo_file_path, 'wb') as f:
            f.write(output)
            
        print(f"Created {mo_file_path} with {len(translations)} translations")
        return True
        
    except Exception as e:
        print(f"Error creating {mo_file_path}: {e}")
        return False

def main():
    """Main function."""
    
    # Process Russian translations
    ru_po = 'locale/ru/LC_MESSAGES/django.po'
    ru_mo = 'locale/ru/LC_MESSAGES/django.mo'
    
    if os.path.exists(ru_po):
        create_mo_file(ru_po, ru_mo)
    else:
        print(f"File {ru_po} not found")
    
    # Process English translations (if exists)
    en_po = 'locale/en/LC_MESSAGES/django.po'
    en_mo = 'locale/en/LC_MESSAGES/django.mo'
    
    if os.path.exists(en_po):
        create_mo_file(en_po, en_mo)
    else:
        print(f"File {en_po} not found")

if __name__ == '__main__':
    main()