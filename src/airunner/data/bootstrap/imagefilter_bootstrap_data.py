from airunner.settings import AIRUNNER_ART_ENABLED


imagefilter_bootstrap_data = {
    'pixel_art': {
        'display_name': 'Pixel Art',
        'auto_apply': False,
        'name': 'pixel_art',
        'filter_class': 'PixelFilter',
        'image_filter_values': {
            'number_of_colors': {
                'name': 'number_of_colors',
                'value': '24',
                'value_type': 'int',
                'min_value': '2',
                'max_value': '1024'
            },
            'smoothing': {
                'name': 'smoothing',
                'value': '0',
                'value_type': 'int',
                'min_value': '0',
                'max_value': '100'
            },
            'base_size': {
                'name': 'base_size',
                'value': '256',
                'value_type': 'int',
                'min_value': '2',
                'max_value': '256'
            },
        }
    },
    'gaussian_blur': {
        'display_name': 'Gaussian Blur',
        'auto_apply': False,
        'name': 'gaussian_blur',
        'filter_class': 'GaussianBlur',
        'image_filter_values': {
            'radius': {
                'name': 'radius',
                'value': '0.0',
                'value_type': 'float',
                'min_value': None,
                'max_value': None
            }
        }
    },
    'box_blur': {
        'display_name': 'Box Blur',
        'auto_apply': False,
        'name': 'box_blur',
        'filter_class': 'BoxBlur',
        'image_filter_values': {
            'radius': {
                'name': 'radius',
                'value': '0.0',
                'value_type': 'float',
                'min_value': None,
                'max_value': None
            }
        }
    },
    'film': {
        'display_name': 'Film',
        'auto_apply': False,
        'name': 'film',
        'filter_class': 'FilmFilter',
        'image_filter_values': {
            'radius': {
                'name': 'radius',
                'value': '0.0',
                'value_type': 'float',
                'min_value': None,
                'max_value': None
            },
            'red': {
                'name': 'red',
                'value': '0.0',
                'value_type': 'float',
                'min_value': None,
                'max_value': None
            },
            'green': {
                'name': 'green',
                'value': '0.0',
                'value_type': 'float',
                'min_value': None,
                'max_value': None
            },
            'blue': {
                'name': 'blue',
                'value': '0.0',
                'value_type': 'float',
                'min_value': None,
                'max_value': None
            },
        }
    },
    'color_balance': {
        'display_name': 'Color Balance',
        'auto_apply': False,
        'name': 'color_balance',
        'filter_class': 'ColorBalanceFilter',
        'image_filter_values': {
            'cyan_red': {
                'name': 'cyan_red',
                'value': '0.0',
                'value_type': 'float',
                'min_value': None,
                'max_value': None
            },
            'magenta_green': {
                'name': 'magenta_green',
                'value': '0.0',
                'value_type': 'float',
                'min_value': None,
                'max_value': None
            },
            'yellow_blue': {
                'name': 'yellow_blue',
                'value': '0.0',
                'value_type': 'float',
                'min_value': None,
                'max_value': None
            }
        }
    },
    'halftone': {
        'display_name': 'Halftone Filter',
        'auto_apply': False,
        'name': 'halftone',
        'filter_class': 'HalftoneFilter',
        'image_filter_values': {
            'sample': {
                'name': 'sample',
                'value': '1',
                'value_type': 'int',
                'min_value': None,
                'max_value': None
            },
            'scale': {
                'name': 'scale',
                'value': '1',
                'value_type': 'int',
                'min_value': None,
                'max_value': None
            },
            'color_mode': {
                'name': 'color_mode',
                'value': 'L',
                'value_type': 'str',
                'min_value': None,
                'max_value': None
            },
        }
    },
    'registration_error': {
        'display_name': 'Registration Error',
        'auto_apply': False,
        'name': 'registration_error',
        'filter_class': 'RegistrationErrorFilter',
        'image_filter_values': {
            'red_offset_x_amount': {
                'name': 'red_offset_x_amount',
                'value': '3',
                'value_type': 'int',
                'min_value': None,
                'max_value': None
            },
            'red_offset_y_amount': {
                'name': 'red_offset_y_amount',
                'value': '3',
                'value_type': 'int',
                'min_value': None,
                'max_value': None
            },
            'green_offset_x_amount': {
                'name': 'green_offset_x_amount',
                'value': '6',
                'value_type': 'int',
                'min_value': None,
                'max_value': None
            },
            'green_offset_y_amount': {
                'name': 'green_offset_y_amount',
                'value': '6',
                'value_type': 'int',
                'min_value': None,
                'max_value': None
            },
            'blue_offset_x_amount': {
                'name': 'blue_offset_x_amount',
                'value': '9',
                'value_type': 'int',
                'min_value': None,
                'max_value': None
            },
            'blue_offset_y_amount': {
                'name': 'blue_offset_y_amount',
                'value': '9',
                'value_type': 'int',
                'min_value': None,
                'max_value': None
            },
        }
    },
    'unsharp_mask': {
        'display_name': 'Unsharp Mask',
        'auto_apply': False,
        'name': 'unsharp_mask',
        'filter_class': 'UnsharpMask',
        'image_filter_values': {
            'radius': {
                'name': 'radius',
                'value': '0.5',
                'value_type': 'float',
                'min_value': None,
                'max_value': None
            },
            'percent': {
                'name': 'percent',
                'value': '0.5',
                'value_type': 'float',
                'min_value': None,
                'max_value': None
            },
            'threshold': {
                'name': 'threshold',
                'value': '0.5',
                'value_type': 'float',
                'min_value': None,
                'max_value': None
            },
        }
    },
    'saturation': {
        'display_name': 'Saturation Filter',
        'auto_apply': False,
        'name': 'saturation',
        'filter_class': 'SaturationFilter',
        'image_filter_values': {
            'factor': {
                'name': 'factor',
                'value': '1.0',
                'value_type': 'float',
                'min_value': None,
                'max_value': None
            },
        }
    },
    'invert': {
        'display_name': 'Invert',
        'auto_apply': False,
        'name': 'invert',
        'filter_class': 'Invert',
        'image_filter_values': {}
    },
    'rgb_noise': {
        'display_name': 'RGB Noise Filter',
        'auto_apply': False,
        'name': 'rgb_noise',
        'filter_class': 'RGBNoiseFilter',
        'image_filter_values': {
            'red': {
                'name': 'red',
                'value': '0.0',
                'value_type': 'float',
                'min_value': None,
                'max_value': None
            },
            'green': {
                'name': 'green',
                'value': '0.0',
                'value_type': 'float',
                'min_value': None,
                'max_value': None
            },
            'blue': {
                'name': 'blue',
                'value': '0.0',
                'value_type': 'float',
                'min_value': None,
                'max_value': None
            },
        }
    }
}


if not AIRUNNER_ART_ENABLED:
    imagefilter_bootstrap_data = {}