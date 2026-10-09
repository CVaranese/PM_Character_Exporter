# PM_Character_Exporter
Export characters from PM, intended to be ported to ROA2.

TODO:
- ~~Brawlcrate plugin to export hitboxes~~
- Brawlcrate plugin to export hurtboxes
- ~~Brawlcrate plugin to export bones~~
- ~~Brawlcrate plugin to export animations~~
    - ~~Disable TRANS bone in animations~~

ISSUES:
    - Animations that turn him around need to be flipped
    - Some attributes are incorrect
    - Missing hitstun animations
    - Landing Lag animations need to be sped up 2x for L cancel
    - Smash attacks have START frames? skip for now?
    - jab multi sub actions

Multi action attacks (jab):
    - Entire animation is loaded into one file
    - Use window cancels to go to next phase
    - ~~To implement: Have all files in separate animations, window cancel into other moves?~~

Angled moves:
    - Entire animation is loaded into one file
    - Window cancels to select different part of the animation
    - ~~To implement: Have all files in separate animations, window cancel into other moves?~~
    - ~~Need to find out how to activate angle before move starts somehow~~
        - solved, slight issue with the animation but itll be fine

~~Update: Will need to merge animations. :c~~

TODO:
- Critical
    - Turn around animations
    - Hurtbox
    - Strong moves
    - Special moves

- Extra
    - Sounds
    - Hurt animations