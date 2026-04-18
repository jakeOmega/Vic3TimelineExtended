import argparse
import os
import torch
from diffusers import FluxPipeline
from PIL import Image

def generate_image(prompt, style, output, model_id, steps, width, height, token):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    
    # Resolve HF token: explicit arg > env var > cached login
    hf_token = token or os.environ.get("HF_TOKEN")
    
    # Load the model with memory-efficient settings for 10GB VRAM
    pipe = FluxPipeline.from_pretrained(
        model_id, 
        torch_dtype=torch.bfloat16,
        token=hf_token,
    )
    pipe.enable_model_cpu_offload()  # offload to CPU when not in use — fits in 10GB VRAM

    # Enhance prompt with style
    full_prompt = f"{prompt}, {style}" if style else prompt
    # Suppress garbled text/writing and common FLUX artifacts
    full_prompt += ", no text, no writing, no watermarks"

    # Generate
    print(f"Generating: '{full_prompt}' ({width}x{height}, {steps} steps)...")
    image = pipe(
        prompt=full_prompt,
        guidance_scale=0.0,
        num_inference_steps=steps,
        max_sequence_length=256,
        width=width,
        height=height,
    ).images[0]

    # Save
    image.save(output)
    print(f"Saved to {output}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Local GenAI Image Tool")
    parser.add_argument("-d", "--description", required=True, help="Image prompt")
    parser.add_argument("-s", "--style", default="realistic", help="Style modifier")
    parser.add_argument("-o", "--output", default="output.png", help="Output filename")
    parser.add_argument("--model", default="black-forest-labs/FLUX.1-schnell", help="HuggingFace Model ID")
    parser.add_argument("--steps", type=int, default=4, help="Inference steps (4 for schnell, 20+ for dev)")
    parser.add_argument("--width", type=int, default=1024, help="Image width (must be multiple of 16)")
    parser.add_argument("--height", type=int, default=1024, help="Image height (must be multiple of 16)")
    parser.add_argument("--token", default=None, help="HuggingFace API token (or set HF_TOKEN env var)")

    args = parser.parse_args()
    generate_image(args.description, args.style, args.output, args.model, args.steps, args.width, args.height, args.token)