I need this workbook fomula converted to a python function. It should take in Damage, WDSK, BKB, and Scaling and output Rivals 2 BKB and Rivals 2 Scaling. I have included the two below examples for your use. The data was extracted from google sheets in TSV format.

-- forumlas executed
diddy	Damage	WDSK	BKB	Scaling	KB at 0	KB at 100	R2KB at 0	R2KB at 100	Rivals 2 BKB	Rivals 2 Scaling
Falcon Bair	14		20	100	38.00	150.00	12.16	48.00	4.05	1.00

-- formulas commented
diddy	Damage	WDSK	BKB	Scaling	KB at 0	KB at 100	R2KB at 0	R2KB at 100	Rivals 2 BKB	Rivals 2 Scaling															
Falcon Bair	14		20	100	=IF(C2<>"", D2+ E2/100*(18 + (1.4*((C2*10)/20 + 1))), D2+ E2/100*(18 + (14*(0)*(B2+2))/200))	=IF(C2<>"", D2+ E2/100*(18 + (1.4*((C2*10)/20 + 1))), D2+ E2/100*(18 + (14*(100)*(B2+2))/200))	=(F2*0.03*10.666)	=(G2*0.03*10.666)	=H2/$P$2	=((I2/$P$2)-(H2/$P$2))/(100*0.12)			Global KB multiplier		3										