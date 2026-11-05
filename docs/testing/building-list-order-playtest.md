# Building list order: play-test

The building list (2026-11-03): the mod's buildings sit beside their vanilla peers, and pollution controls follow the production groups in a building's production methods. The building browser's default sort and its Building Type column are the order building definitions load, which follows file names (`docs/guides/scripting_best_practices.md` § Load Order (probed 2026-10-26), "Building list order"). The file names were checked offline (`test_building_list_order.py`); what the game shows was not.

## How to run

Load a late game with a wide spread of buildings (the France test game serves). Open the building browser (All Buildings, default sort) and a state's buildings. Then open the production methods of the buildings in step 3.

## Checks

1. **Sector order.** Under the default sort (or Building Type):
   - Consumer Appliance, Semiconductor, Robotics, Software and Aerospace Industries follow Munitions Plants, and Food Industries is still first.
   - The new mines follow Gold Fields.
   - Military Base, the Ground-to-Orbit Battery and Space Command follow the Army Logistics Center.
   - Hydro, Nuclear, Renewable Energy and Fusion Plants and the Grid Transfer Station follow Power Plant.
   - State Youth Centers, Public Housing, the Settlement Authority and the Strategic Reserve buildings follow Skyscrapers.
   - Grand Monuments, National Park, Tourism Industry and the wonders follow the vanilla monuments.
   - Airport, Highway and Network Infrastructure follow Financial Districts.
   - Company buildings still follow Company Headquarters, and the space buildings and megastructures close the list.

   If the mod's buildings all sit at the end in their old order, the engine sorts the list some other way than load order. Report it rather than renaming more files.
2. **Nothing lost.** Each building the state had before the update is still listed, at the same level. Nothing has lost its icon or name.
3. **Pollution controls last.** These buildings show carbon capture after their production groups, not before: Furniture Manufacturies (after Marketing), Chemical Plants and Explosives Factories (after automation), Power Plants (after automation), Shipyards (after the focus group) and Oil Rigs (after depth).
4. **An old save keeps its methods.** Load a save made before the update. Pick a building from step 3 that has carbon capture switched on, and one with a non-default method in the group that moved. Both keep their chosen methods. The groups only changed order, so a save that stores methods by name won't notice.
