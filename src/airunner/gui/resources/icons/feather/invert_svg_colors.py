#!/usr/bin/env python3
import sys
import re
from lxml import etree

def invert_color(color_str):
    # Handle hex colors
    if color_str.startswith('#'):
        hex_color = color_str.lstrip('#')
        if len(hex_color) == 3:
            r = int(hex_color[0] + hex_color[0], 16)
            g = int(hex_color[1] + hex_color[1], 16)
            b = int(hex_color[2] + hex_color[2], 16)
        else:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
        
        # Special case for black and white
        if r == 0 and g == 0 and b == 0:
            return '#ffffff'
        elif r == 255 and g == 255 and b == 255:
            return '#000000'
        else:
            r, g, b = 255 - r, 255 - g, 255 - b
            return f'#{r:02x}{g:02x}{b:02x}'
    
    # Handle named colors
    elif color_str == 'black':
        return 'white'
    elif color_str == 'white':
        return 'black'
    
    # Handle rgb format
    rgb_match = re.match(r'rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', color_str)
    if rgb_match:
        r = int(rgb_match.group(1))
        g = int(rgb_match.group(2))
        b = int(rgb_match.group(3))
        
        if r == 0 and g == 0 and b == 0:
            return 'rgb(255, 255, 255)'
        elif r == 255 and g == 255 and b == 255:
            return 'rgb(0, 0, 0)'
        else:
            r, g, b = 255 - r, 255 - g, 255 - b
            return f'rgb({r}, {g}, {b})'
    
    # Return unchanged if not a recognized color format
    return color_str

def process_svg(input_file, output_file):
    try:
        # Parse the SVG file
        parser = etree.XMLParser(remove_blank_text=True)
        tree = etree.parse(input_file, parser)
        root = tree.getroot()
        
        # Find all elements with color attributes
        color_attrs = ['fill', 'stroke', 'color', 'stop-color']
        
        # Process all elements
        for elem in root.iter():
            # Process style attribute
            if 'style' in elem.attrib:
                style = elem.attrib['style']
                for prop in style.split(';'):
                    if ':' in prop:
                        name, value = prop.split(':', 1)
                        name = name.strip()
                        value = value.strip()
                        if name in color_attrs and value not in ['none', 'transparent']:
                            new_value = invert_color(value)
                            style = style.replace(f'{name}:{value}', f'{name}:{new_value}')
                elem.attrib['style'] = style
            
            # Process direct color attributes
            for attr in color_attrs:
                if attr in elem.attrib and elem.attrib[attr] not in ['none', 'transparent']:
                    elem.attrib[attr] = invert_color(elem.attrib[attr])
        
        # Write the modified SVG
        tree.write(output_file, pretty_print=True, encoding='utf-8', xml_declaration=True)
        print(f"Successfully wrote inverted SVG to {output_file}")
        return True
        
    except Exception as e:
        print(f"Error processing file: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python invert_svg_colors.py input.svg output.svg")
        sys.exit(1)
    
    success = process_svg(sys.argv[1], sys.argv[2])
    sys.exit(0 if success else 1)
