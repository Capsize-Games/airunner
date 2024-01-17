imagefilter_bootstrap_data = [
    {
        'display_name': 'Pixel Art',
        'name': 'pixel_art',
        'filter_class': 'PixelFilter',
        'image_filter_values': [
            {'name': 'number_of_colors', 'value': '24', 'value_type': 'int', 'min_value': '2', 'max_value': '1024'},
            {'name': 'smoothing', 'value': '1', 'value_type': 'int', 'min_value': None, 'max_value': None},
            {'name': 'base_size', 'value': '256', 'value_type': 'int', 'min_value': '2', 'max_value': '256'}
        ]
    },
    {
        'display_name': 'Gaussian Blur',
        'name': 'gaussian_blur',
        'filter_class': 'GaussianBlur',
        'image_filter_values': [
            {'name': 'radius', 'value': '0.0', 'value_type': 'float', 'min_value': None, 'max_value': None}
        ]
    },
    {
        'display_name': 'Box Blur',
        'name': 'box_blur',
        'filter_class': 'BoxBlur',
        'image_filter_values': [
            {'name': 'radius', 'value': '0.0', 'value_type': 'float', 'min_value': None, 'max_value': None}
        ]
    },
    {
        'display_name': 'Color Balance',
        'name': 'color_balance',
        'filter_class': 'ColorBalanceFilter',
        'image_filter_values': [
            {'name': 'cyan_red', 'value': '0.0', 'value_type': 'float', 'min_value': None, 'max_value': None},
            {'name': 'magenta_green', 'value': '0.0', 'value_type': 'float', 'min_value': None, 'max_value': None},
            {'name': 'yellow_blue', 'value': '0.0', 'value_type': 'float', 'min_value': None, 'max_value': None}
        ]
    },
    {
        'display_name': 'Halftone Filter',
        'name': 'halftone',
        'filter_class': 'HalftoneFilter',
        'image_filter_values': [
            {'name': 'sample', 'value': '1', 'value_type': 'int', 'min_value': None, 'max_value': None},
            {'name': 'scale', 'value': '1', 'value_type': 'int', 'min_value': None, 'max_value': None},
            {'name': 'color_mode', 'value': 'L', 'value_type': 'str', 'min_value': None, 'max_value': None}
        ]
    },
    {
        'display_name': 'Registration Error',
        'name': 'registration_error',
        'filter_class': 'RegistrationErrorFilter',
        'image_filter_values': [
            {'name': 'red_offset_x_amount', 'value': '3', 'value_type': 'int', 'min_value': None, 'max_value': None},
            {'name': 'red_offset_y_amount', 'value': '3', 'value_type': 'int', 'min_value': None, 'max_value': None},
            {'name': 'green_offset_x_amount', 'value': '6', 'value_type': 'int', 'min_value': None, 'max_value': None},
            {'name': 'green_offset_y_amount', 'value': '6', 'value_type': 'int', 'min_value': None, 'max_value': None},
            {'name': 'blue_offset_x_amount', 'value': '9', 'value_type': 'int', 'min_value': None, 'max_value': None},
            {'name': 'blue_offset_y_amount', 'value': '9', 'value_type': 'int', 'min_value': None, 'max_value': None}
        ]
    },
    {
        'display_name': 'Unsharp Mask',
        'name': 'unsharp_mask',
        'filter_class': 'UnsharpMask',
        'image_filter_values': [
            {'name': 'radius', 'value': '0.5', 'value_type': 'float', 'min_value': None, 'max_value': None},
            {'name': 'percent', 'value': '0.5', 'value_type': 'float', 'min_value': None, 'max_value': None},
            {'name': 'threshold', 'value': '0.5', 'value_type': 'float', 'min_value': None, 'max_value': None}
        ]
    },
    {
        'display_name': 'Saturation Filter',
        'name': 'saturation',
        'filter_class': 'SaturationFilter',
        'image_filter_values': [
            {'name': 'factor', 'value': '1.0', 'value_type': 'float', 'min_value': None, 'max_value': None}
        ]
    },
    {
        'display_name': 'RGB Noise Filter',
        'name': 'rgb_noise',
        'filter_class': 'RGBNoiseFilter',
        'image_filter_values': [
            {'name': 'red', 'value': '0.0', 'value_type': 'float', 'min_value': None, 'max_value': None},
            {'name': 'green', 'value': '0.0', 'value_type': 'float', 'min_value': None, 'max_value': None},
            {'name': 'blue', 'value': '0.0', 'value_type': 'float', 'min_value': None, 'max_value': None}
        ]
    }
]