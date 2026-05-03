mod_path = r"/home/jakef/src/Vic3TimelineExtended"
base_game_path = r"/mnt/c/Program Files (x86)/Steam/steamapps/common/Victoria 3"
doc_path = r"/home/jakef/src/Vic3TimelineExtended/docs"
mod_deploy_target = r"/mnt/c/Users/jakef/OneDrive/Documents/Paradox Interactive/Victoria 3/mod/Vic3TimelineExtended"

# Engine docs (script_docs output): two sources, used together for vanilla-vs-mod
# disambiguation. The runtime path is whatever the user last wrote there by typing
# `script_docs` in the in-game console — it could be vanilla-loaded OR mod-loaded
# depending on context. The repo-mirror path is a vanilla-only snapshot; treat it
# as the authoritative baseline. See docs/python_tools.md.
vanilla_snapshot_docs_path = r"/home/jakef/src/vic3/docs"        # authoritative vanilla baseline
vanilla_source_repo_path = r"/home/jakef/src/vic3"               # vanilla source mirror; HEAD commit date = "current vanilla version" proxy
vanilla_docs_path = r"/mnt/c/Users/jakef/OneDrive/Documents/Paradox Interactive/Victoria 3/docs"  # runtime path; legacy name kept for back-compat
mod_loaded_docs_path = vanilla_docs_path                          # alias; same path, clearer intent

game_logs_path = r"/mnt/c/Users/jakef/OneDrive/Documents/Paradox Interactive/Victoria 3/logs"
