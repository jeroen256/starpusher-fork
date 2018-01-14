# Starpusher-Fork

This game is copied from:
http://inventwithpython.com/pygame/

I really enjoy playing it, big thanks to Al Sweigart!

Extra features added:
- Remember level and gamestate
- ALT + Arrow: keep walking
- CTRL + Arrow: walk 5 steps
- SHIFT + Arrow: walk to the end of the line
- CTRL + Z: undo
- Mouseclick: teleport / automatic walking. 
  - Save some serious time with repeating tasks! :)
  - Game rules still apply. Cheating is not really possible, although that would have been a lot easier to implement. ;)
  - Click anywhere to request the player to be moved there.
  - Click on a star to select it. Then click anywhere to request the star to be moved there.
  - Shortest route is calculated with BFS (Breadth First Search), a function to find the shortest path in a maze between a given source cell to a destination cell. 
  - https://www.geeksforgeeks.org/shortest-path-in-a-binary-maze/
  - Step counter is increased accordingly.
- Window resizable
- F: toggle fullscreen

In case of any error, delete the "settings.pkl" file.
If that doens't resolve it, also delete the "settings.json" file.
These files contain the saved game state. 
Sometimes a newer version comes out that can't handle the older game state.

Github: https://github.com/jeroen256/starpusher-fork

Enjoy playing!

