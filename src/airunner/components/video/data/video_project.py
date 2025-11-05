"""Video project data model for storing video generation metadata."""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    LargeBinary,
)

from airunner.components.data.models.base import BaseModel


class VideoProject(BaseModel):
    """
    Stores metadata and settings for video generation projects.

    Attributes:
        id: Primary key
        name: Project name
        model_name: Name of the video model used (HunyuanVideo, CogVideoX, etc.)
        model_path: Path to the model
        prompt: Text prompt for generation
        negative_prompt: Negative text prompt
        seed: Random seed for reproducibility
        num_frames: Number of frames to generate
        fps: Frames per second for output video
        width: Video width in pixels
        height: Video height in pixels
        guidance_scale: CFG scale for generation
        num_inference_steps: Number of denoising steps
        strength: Strength for image-to-video (0.0-1.0)
        init_image_path: Path to initial image for I2V
        init_image: Binary data of initial image
        output_path: Path to generated video file
        is_complete: Whether generation is complete
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "video_projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, default="Untitled Video")

    # Model configuration
    model_name = Column(String, nullable=False, default="HunyuanVideo")
    model_path = Column(String, nullable=False, default="")

    # Generation parameters
    prompt = Column(String, nullable=False, default="")
    negative_prompt = Column(String, nullable=False, default="")
    seed = Column(Integer, nullable=False, default=-1)
    num_frames = Column(Integer, nullable=False, default=16)
    fps = Column(Integer, nullable=False, default=8)
    width = Column(Integer, nullable=False, default=512)
    height = Column(Integer, nullable=False, default=512)
    guidance_scale = Column(Float, nullable=False, default=7.5)
    num_inference_steps = Column(Integer, nullable=False, default=50)

    # Image-to-video parameters
    strength = Column(Float, nullable=False, default=0.8)
    init_image_path = Column(String, nullable=True, default="")
    init_image = Column(LargeBinary, nullable=True)

    # Output
    output_path = Column(String, nullable=False, default="")
    is_complete = Column(Boolean, nullable=False, default=False)
