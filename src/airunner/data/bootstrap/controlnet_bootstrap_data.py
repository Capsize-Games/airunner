from airunner.settings import AIRUNNER_ART_ENABLED


controlnet_bootstrap_data = [
    {"display_name": "Canny", "name": "canny", "path": "lllyasviel/control_v11p_sd15_canny", "version": "SD 1.5"},
    {"display_name": "Depth Leres", "name": "depth_leres", "path": "lllyasviel/control_v11f1p_sd15_depth", "version": "SD 1.5"},
    {"display_name": "Depth Leres++", "name": "depth_leres++", "path": "lllyasviel/control_v11f1p_sd15_depth", "version": "SD 1.5"},
    {"display_name": "Depth Midas", "name": "depth_midas", "path": "lllyasviel/control_v11f1p_sd15_depth", "version": "SD 1.5"},
    {"display_name": "Depth Zoe", "name": "depth_zoe", "path": "lllyasviel/control_v11f1p_sd15_depth", "version": "SD 1.5"},
    {"display_name": "MLSD", "name": "mlsd", "path": "lllyasviel/control_v11p_sd15_mlsd", "version": "SD 1.5"},
    {"display_name": "Normal Bae", "name": "normal_bae", "path": "lllyasviel/control_v11p_sd15_normalbae", "version": "SD 1.5"},
    {"display_name": "Normal Midas", "name": "normal_midas", "path": "lllyasviel/control_v11p_sd15_normalbae", "version": "SD 1.5"},
    {"display_name": "Scribble Hed", "name": "scribble_hed", "path": "lllyasviel/control_v11p_sd15_scribble", "version": "SD 1.5"},
    {"display_name": "Scribble Pidinet", "name": "scribble_pidinet", "path": "lllyasviel/control_v11p_sd15_scribble", "version": "SD 1.5"},
    {"display_name": "Segmentation", "name": "segmentation", "path": "lllyasviel/control_v11p_sd15_seg", "version": "SD 1.5"},
    {"display_name": "Lineart Coarse", "name": "lineart_coarse", "path": "lllyasviel/control_v11p_sd15_lineart", "version": "SD 1.5"},
    {"display_name": "Lineart Realistic", "name": "lineart_realistic", "path": "lllyasviel/control_v11p_sd15_lineart", "version": "SD 1.5"},
    {"display_name": "Lineart Anime", "name": "lineart_anime", "path": "lllyasviel/control_v11p_sd15s2_lineart_anime", "version": "SD 1.5"},
    {"display_name": "Openpose", "name": "openpose", "path": "lllyasviel/control_v11p_sd15_openpose", "version": "SD 1.5"},
    {"display_name": "Openpose Face", "name": "openpose_face", "path": "lllyasviel/control_v11p_sd15_openpose", "version": "SD 1.5"},
    {"display_name": "Openpose Faceonly", "name": "openpose_faceonly", "path": "lllyasviel/control_v11p_sd15_openpose", "version": "SD 1.5"},
    {"display_name": "Openpose Full", "name": "openpose_full", "path": "lllyasviel/control_v11p_sd15_openpose", "version": "SD 1.5"},
    {"display_name": "Openpose Hand", "name": "openpose_hand", "path": "lllyasviel/control_v11p_sd15_openpose", "version": "SD 1.5"},
    {"display_name": "Scribble Hed", "name": "softedge_hed", "path": "lllyasviel/control_v11p_sd15_softedge", "version": "SD 1.5"},
    {"display_name": "Softedge Hedsafe", "name": "softedge_hedsafe", "path": "lllyasviel/control_v11p_sd15_softedge", "version": "SD 1.5"},
    {"display_name": "Scribble Pidinet", "name": "softedge_pidinet", "path": "lllyasviel/control_v11p_sd15_softedge", "version": "SD 1.5"},
    {"display_name": "Softedge Pidsafe", "name": "softedge_pidsafe", "path": "lllyasviel/control_v11p_sd15_softedge", "version": "SD 1.5"},
    {"display_name": "Pixel2Pixel", "name": "pixel2pixel", "path": "lllyasviel/control_v11e_sd15_ip2p", "version": "SD 1.5"},
    {"display_name": "Inpaint", "name": "inpaint", "path": "lllyasviel/control_v11p_sd15_inpaint", "version": "SD 1.5"},
    {"display_name": "Shuffle", "name": "shuffle", "path": "lllyasviel/control_v11e_sd15_shuffle", "version": "SD 1.5"},
    {"display_name": "Canny", "name": "canny", "path": "diffusers/controlnet-canny-sdxl-1.0-small", "version": "SDXL 1.0"},
]


if not AIRUNNER_ART_ENABLED:
    controlnet_bootstrap_data = []