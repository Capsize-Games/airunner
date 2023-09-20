imagefilter_bootstrap_data = (
    ("Pixel Art", "pixel_art", "PixelFilter", (
        ("number_of_colors", "24", "int", "2", "1024"),
        ("smoothing", "1", "int"),
        ("base_size", "256", "int", "2", "256"),
    )),
    ("Gaussian Blur", "gaussian_blur", "GaussianBlur", (
        ("radius", "0.0", "float"),
    )),
    ("Box Blur", "box_blur", "BoxBlur", (
        ("radius", "0.0", "float"),
    )),
    ("Color Balance", "color_balance", "ColorBalanceFilter", (
        ("cyan_red", "0.0", "float"),
        ("magenta_green", "0.0", "float"),
        ("yellow_blue", "0.0", "float"),
    )),
    ("Halftone Filter", "halftone", "HalftoneFilter", (
        ("sample", "1", "int"),
        ("scale", "1", "int"),
        ("color_mode", "L", "str"),
    )),
    ("Registration Error", "registration_error", "RegistrationErrorFilter", (
        ("red_offset_x_amount", "3", "int"),
        ("red_offset_y_amount", "3", "int"),
        ("green_offset_x_amount", "6", "int"),
        ("green_offset_y_amount", "6", "int"),
        ("blue_offset_x_amount", "9", "int"),
        ("blue_offset_y_amount", "9", "int")
    )),
    ("Unsharp Mask", "unsharp_mask", "UnsharpMask", (
        ("radius", "0.5", "float"),
        ("percent", "0.5", "float"),
        ("threshold", "0.5", "float"),
    )),
    ("Saturation Filter", "saturation", "SaturationFilter", (
        ("factor", "1.0", "float"),
    )),
    ("RGB Noise Filter", "rgb_noise", "RGBNoiseFilter", (
        ("red", "0.0", "float"),
        ("green", "0.0", "float"),
        ("blue", "0.0", "float")
    )),
)