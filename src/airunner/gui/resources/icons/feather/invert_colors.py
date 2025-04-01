#!/usr/bin/env python3
import sys
import os
import re
from xml.dom import minidom

def debug_print(message):
    """Print debug message with prefix"""
    print(f"DEBUG: {message}")

def invert_color(color):
    """Invert any color format found in SVG"""
    # Skip non-color values
    if color in ['none', 'transparent', 'inherit', '']:
        return color
        
    # Handle hex colors (#RGB or #RRGGBB)
    if color.startswith('#'):
        hex_value = color[1:]
        # Convert short hex (#RGB) to long form (#RRGGBB)
        if len(hex_value) == 3:
            hex_value = ''.join([c+c for c in hex_value])
        
        if len(hex_value) == 6:
            # Convert hex to RGB
            r = int(hex_value[0:2], 16)
            g = int(hex_value[2:4], 16)
            b = int(hex_value[4:6], 16)
            
            # Invert colors
            r = 255 - r
            g = 255 - g
            b = 255 - b
            
            # Return as hex
            return f'#{r:02x}{g:02x}{b:02x}'
    
    # Handle rgb(r,g,b) format
    rgb_match = re.match(r'rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', color)
    if rgb_match:
        r = int(rgb_match.group(1))
        g = int(rgb_match.group(2))
        b = int(rgb_match.group(3))
        
        # Invert colors
        r = 255 - r
        g = 255 - g
        b = 255 - b
        
        return f'rgb({r}, {g}, {b})'
    
    # Handle named colors
    named_colors = {
        'black': 'white',
        'white': 'black',
        'red': 'cyan',
        'cyan': 'red',
        'blue': 'yellow',
        'yellow': 'blue',
        'green': 'magenta',
        'magenta': 'green'
    }
    
    if color.lower() in named_colors:
        return named_colors[color.lower()]
    
    # Return unchanged if not a color we recognize or can invert
    return color

def process_svg(input_path, output_path):
    try:
        # Parse SVG file
        with open(input_path, 'r') as f:
            svg_content = f.read()
            
        # Parse using minidom for simplicity
        dom = minidom.parseString(svg_content)
        
        # Colors can be in attributes or in style properties
        color_attrs = ['fill', 'stroke']
        
        # Process all elements for direct color attributes
        elements = dom.getElementsByTagName('*')
        for element in elements:
            # Direct attributes
            for attr in color_attrs:
                if element.hasAttribute(attr):
                    color = element.getAttribute(attr)
                    if color not in ['none', 'transparent']:
                        inverted = invert_color(color)
                        if inverted != color:
                            debug_print(f"Inverting {attr}='{color}' to '{inverted}'")
                            element.setAttribute(attr, inverted)
            
            # Style attribute
            if element.hasAttribute('style'):
                style = element.getAttribute('style')
                new_style = style
                
                # Process each style declaration
                for decl in style.split(';'):
                    if ':' in decl:
                        prop, value = decl.split(':', 1)
                        prop = prop.strip()
                        value = value.strip()
                        
                        if prop in color_attrs and value not in ['none', 'transparent']:
                            inverted = invert_color(value)
                            if inverted != value:
                                debug_print(f"Inverting style {prop}:'{value}' to '{inverted}'")
                                new_style = new_style.replace(f"{prop}:{value}", f"{prop}:{inverted}")
                
                if new_style != style:
                    element.setAttribute('style', new_style)
        
        # Write to output file
        with open(output_path, 'w') as f:
            # The prettify() adds extra whitespace but makes debugging easier
            f.write(dom.toxml())
            
        debug_print(f"Successfully created {os.path.basename(output_path)}")
        return True
    
    except Exception as e:
        print(f"ERROR processing file: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python invert_colors.py input.svg output.svg")
        sys.exit(1)
        
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    debug_print(f"Processing {os.path.basename(input_file)} → {os.path.basename(output_file)}")
    success = process_svg(input_file, output_file)
    
    sys.exit(0 if success else 1)
