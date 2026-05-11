"""
One-shot batch generator for the four missing marine combat-unit illustrations.
Loads FLUX.1-schnell once, runs 4-5 variants per tier, saves PNGs into
gfx/unit_illustrations/_proposed_marines/ for the user to choose winners.

Tiers and their thematic anchors (from common/combat_unit_types/extra_combat_units.txt):
- combined_arms_marines (era 6): WWII / early-Cold-War amphibious assault, GIs from
  landing craft, bomber support overhead
- stealth_marines (era 8): special-forces night insertion, low-signature kit,
  stealth boat/helicopter, contemporary
- networked_marines (era 10, jadc2): near-future marines + drone swarms + HUDs +
  exoskeletons + orbital insertion
- bioenhanced_marines (era 11): far-future gene-augmented operators, energy weapons,
  exotic atmosphere
"""
import os, sys, argparse, gc
import torch
from diffusers import FluxPipeline

# Common style suffix tuned to match vanilla Vic3 marine illustrations
# (painterly oil-render) and mod late-era illustrations (cinematic concept art).
COMMON_STYLE = (
    "Victoria 3 unit illustration style, painterly oil-rendered digital painting, "
    "dramatic atmospheric lighting, cinematic composition, military concept art, "
    "centered focal figure, no text, no writing, no watermarks, no logos"
)

# Per-tier prompt sets. Each variant emphasizes a different framing so the user
# has visually distinct picks.
PROMPTS = {
    "combined_arms": [
        "early Cold War amphibious assault marines wading ashore from a Higgins landing craft, "
        "steel helmets and webbing, M1 Garand rifles, smoke from naval bombardment behind them, "
        "bomber aircraft overhead, contested rocky beach",

        "Pacific theater marines breaching a contested coastline at sunrise, palm trees and "
        "smoke in the distance, marines climbing wet sand with rifles raised, landing craft "
        "disgorging troops behind, Sherman tank emerging from surf",

        "WWII Mediterranean amphibious landing, armored infantry marines with combined-arms "
        "support, light tank rolling off an LST in the background, bomber strike on coastal "
        "fortifications, gritty painterly style",

        "marines disembarking onto a misty European beach at dawn, helmeted figures in long "
        "coats, naval destroyer offshore, bomber formation overhead, oil-painting style",

        "combined-arms marine assault force in foreground, two soldiers with rifles and one "
        "with a radio, light tank surfacing from a landing craft mid-frame, rocket-firing "
        "aircraft strafing the cliff above the beach",
    ],
    "stealth": [
        "modern special-forces marines at night beach insertion, rigid-hull inflatable boat "
        "beaching, four operators in low-visibility kit with night-vision goggles wading "
        "ashore with suppressed carbines, moonlight on dark water",

        "stealth helicopter hovering low over a coastline at dusk, special-forces marines "
        "fast-roping onto sand, faint silhouettes, low-visibility uniforms, cinematic dark "
        "blue palette",

        "combat divers emerging from black surf at night, rebreathers and waterproof gear, "
        "weapons drawn, distant freighter on horizon, dramatic moonlit composition",

        "stealth special-forces marines on a rocky cliff at twilight, suppressed weapons, "
        "muted camo, gas masks, smoke grenades, low-profile silhouette against dim sky",

        "carrier-launched stealth fast boat racing toward shore at night, several marines "
        "on deck with carbines, spray and low waves, distant aircraft carrier silhouette",
    ],
    "networked": [
        "near-future marines in powered exoskeletons wading ashore on a beach, helmet "
        "heads-up displays glowing blue, swarm of small quadcopter surveillance drones "
        "overhead, tactical AR holograms hovering in front of them",

        "orbital drop pod opening on a contested coastline at dawn, marines deploying out "
        "with rifles, faint blue data-link tracers between squad members, futuristic LCAC "
        "hovercraft visible behind, sci-fi military concept art",

        "marines wading ashore with tablet-like wrist displays, quadcopter drones around "
        "them, AI-coordinated movement, modular plate armor, dramatic overcast lighting, "
        "jadc2 networked combat",

        "marines and humanoid combat robots advancing together up a beach, glowing data "
        "links visualized as light tracers, futuristic landing craft behind, sunset palette",

        "first-person near-future combat scene, marines with helmet HUD overlays advancing "
        "up sand at night, drone swarm overhead casting downlight, AR target indicators "
        "floating in the air",
    ],
    "bioenhanced": [
        "tall gene-augmented marines emerging from breaking surf, glowing veins visible on "
        "exposed skin, sleek black armor with bioluminescent accents, exotic moon in a "
        "purple sky, far-future combat concept art",

        "genetically-enhanced super-soldier marines on a beach firing directed-energy "
        "weapons inland, gleaming sci-fi powered armor, nanoswarm cloud above them, "
        "crystalline alien structures along the shore",

        "augmented marine operator in tight foreground composition, standard human marines "
        "for scale contrast behind, exotic shoreline at dusk with bioluminescent ocean, "
        "sci-fi painterly style",

        "bioenhanced marine soldiers in symbiotic black powered armor wading ashore, "
        "drama-lit low-key composition, ocean glowing softly with bioluminescence, dark "
        "purple sky, atmospheric far-future military art",

        "heavy-augment marines with massive enhanced physique firing plasma weapons from a "
        "rocky shoreline, smaller drone-marine fireteam in support, antimatter strike "
        "flash on horizon, sci-fi concept painting",
    ],
}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--outdir", default="gfx/unit_illustrations/_proposed_marines")
    # 1024x1024 OOMs FLUX-schnell on a 10GB RTX 3080 (attention activations blow past
    # the working set even with enable_model_cpu_offload). 768 is the sweet spot.
    p.add_argument("--width", type=int, default=768)
    p.add_argument("--height", type=int, default=768)
    p.add_argument("--steps", type=int, default=4)
    p.add_argument("--seed-base", type=int, default=42, help="Per-variant seeds = seed_base + variant_index")
    p.add_argument("--only", default=None, help="Comma-separated tier names to run (e.g. combined_arms,stealth)")
    p.add_argument("--token", default=None)
    p.add_argument("--seq-cpu-offload", action="store_true",
                   help="Use enable_sequential_cpu_offload (much slower but lowest VRAM); only needed if --width >= 1024 OOMs.")
    args = p.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    token = args.token or os.environ.get("HF_TOKEN")

    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        free, total = torch.cuda.mem_get_info()
        print(f"VRAM at start: {free/1e9:.1f}/{total/1e9:.1f} GB free")
    print(f"Loading FLUX.1-schnell (device: {'cuda' if torch.cuda.is_available() else 'cpu'})...")
    pipe = FluxPipeline.from_pretrained(
        "black-forest-labs/FLUX.1-schnell",
        torch_dtype=torch.bfloat16,
        token=token,
    )
    if args.seq_cpu_offload:
        pipe.enable_sequential_cpu_offload()
    else:
        pipe.enable_model_cpu_offload()
    if hasattr(pipe, "vae") and hasattr(pipe.vae, "enable_slicing"):
        pipe.vae.enable_slicing()
    if hasattr(pipe, "vae") and hasattr(pipe.vae, "enable_tiling"):
        pipe.vae.enable_tiling()

    only = set(args.only.split(",")) if args.only else None
    total = 0
    for tier, prompts in PROMPTS.items():
        if only and tier not in only:
            continue
        for i, prompt in enumerate(prompts, start=1):
            out = os.path.join(args.outdir, f"marines_{tier}_v{i}.png")
            if os.path.exists(out):
                print(f"  SKIP existing: {out}")
                continue
            full = f"{prompt}, {COMMON_STYLE}"
            seed = args.seed_base + i
            print(f"\n[{tier} v{i}] seed={seed} {prompt[:80]}...")
            gen = torch.Generator(device="cpu").manual_seed(seed)
            img = pipe(
                prompt=full,
                guidance_scale=0.0,
                num_inference_steps=args.steps,
                max_sequence_length=256,
                width=args.width,
                height=args.height,
                generator=gen,
            ).images[0]
            img.save(out)
            print(f"  -> {out}")
            total += 1
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
    print(f"\nDone. Generated {total} images into {args.outdir}/")

if __name__ == "__main__":
    main()
