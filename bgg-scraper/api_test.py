from boardgamegeek import BGGClient

bgg = BGGClient("")

game = bgg.game("Monopoly")

print(game.year)  # 1935
print(game.rating_average)  # 4.36166