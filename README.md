# Genius Invokation TCG Simulator

This is a simulator for Genius Invokation TCG, which is a built-in game of Genshin Impact.

Please note that this simulator is designed for (RL) research, I don't have any copyrights of the game.
Game data is borrowed from [this URL](https://www.ign.com/wikis/genshin-impact/Genius_Invokation:_All_Genshin_TCG_Cards), [this Wiki](https://genshin-impact.fandom.com/wiki/Genius_Invokation_TCG/Card_List) and [this Chinese Wiki](https://wiki.biligame.com/ys/%E4%B8%83%E5%9C%A3%E5%8F%AC%E5%94%A4).

---
## This project is still under construction. 

```
Progress
[Characters] 3 / 27
[Actions] 31 / 117
```

## Dependence
```
pip install numpy
```

## Demo

Edit ```p1.json``` and ```p2.json```  to change the card deck.
```
python game.py
```

## TODO
1. Elemental reactions: electro, hydro, dendro, geo
2. Support card, weapon, artifact equipment system
3. Summons: now beta
4. More characters and action cards
5. Debug - I really need some help to test this code. Please report any bugs you found via issue, and include as many as logs if possible. Thank you so much for your contribution! 

## Update log
12/20/22:
1. Add some Elemental Resonance cards and some event cards
2. reorganize the game loop structure

12/19/22:
1. Finish basic skill pipeline
2. Better character switch pipeline when one character is dead
3. Buff from foods is done
4. Add swap card phase at the beginning of the game
5. Summons is beta now
6. Add Anemo reactions


12/18/22:
1. Build basic concepts including characters, actions, dice, deck and game framework.
2. Finish the game pipeline and add the first action card "Sweet Madame"
3. Init buff system and add all food cards
