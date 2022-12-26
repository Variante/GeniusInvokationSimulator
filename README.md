# Genius Invokation TCG Simulator

This is a simulator for Genius Invokation TCG, which is a built-in game of Genshin Impact.

Please note that this simulator is designed for (RL) research, I don't have any copyrights of the game.
Game data is borrowed from [this URL](https://www.ign.com/wikis/genshin-impact/Genius_Invokation:_All_Genshin_TCG_Cards), [this Wiki](https://genshin-impact.fandom.com/wiki/Genius_Invokation_TCG/Card_List) and [this Chinese Wiki](https://wiki.biligame.com/ys/%E4%B8%83%E5%9C%A3%E5%8F%AC%E5%94%A4).

中文用户请参考[这个文档](https://docs.qq.com/doc/DSWRKbVRHRlhnaUJt)

---
## This project is still under construction. But we are close to finish... I guess

```
Progress
[Characters] 20 / 27
[Actions] 110 / 119
```

## Dependence
```
pip install numpy tqdm
```

## Demo

Edit ```p1.json``` and ```p2.json```  to change the card deck.
```
python game.py
```

## TODO
1. UI solution
1. Better buff system (team buff + personal buff)
2. More characters and more talent card => current talent sysment may need to be redesigned
3. Deck check, not all cards can be included in a deck
4. Debug - I really need some help to test this code. Please report any bugs you found via issue, and include as many as logs if possible. Thank you so much for your contribution! 

## Update log
12/25/22:
1. Add new characters
2. All reactions are done
3. Fix summon bug - not activated at the end of a round


12/24/22:
1. Add Kamisato Ayaka
2. Buff system now can recognize 'refresh', 'stay' and 'unique' tags

12/23/22:
1. Reorganize a lot of code, add (almost) all cards except talent cards
2. Add more Cryo characters

12/22/22:
1. Finished most of the event cards and all support cards
2. Add Fischl

12/21/22:
1. Add all artifact cards, now Artifact sys is beta
2. Add save function, now we can export all the states
3. Start to build support cards

12/20/22:
1. Add some Elemental Resonance cards and some event cards
2. Reorganize the game loop structure
3. Init equipment system
4. Add two talent cards and all weapon cards
5. Add shield system

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
