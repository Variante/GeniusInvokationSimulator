# Genius Invokation Simulator

This is a simulator of Genius Invokation, which is a built-in game of Genshin Impact. 

Please note that this simulator is designed for (RL) research, I don't have any copyrights of the game.
Game data is borrowed from [this URL](https://www.ign.com/wikis/genshin-impact/Genius_Invokation:_All_Genshin_TCG_Cards).

---
## This project is still under construction. 

## Dependence
```
pip install numpy
```

## Demo
```
python game.py
```

## TODO
1. The effect of buffs and debuffs
2. Elemental reactions
3. More characters and action cards

## Update log
12/19/22:
1. Finish basic skill pipeline
2. Better character switch pipeline when one character is dead
3. Buff from foods is done


12/18/22:
1. Build basic concepts including characters, actions, dice, deck and game framework.
2. Finish the game pipeline and add the first action card "Sweet Madame"
3. Init buff system and add all food cards
