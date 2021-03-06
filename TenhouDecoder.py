#! /usr/bin/python3

import xml.etree.ElementTree as etree
import urllib.parse
from Data import Data

class Tile(Data, int):
    UNICODE_TILES = """
        🀐 🀑 🀒 🀓 🀔 🀕 🀖 🀗 🀘
        🀙 🀚 🀛 🀜 🀝 🀞 🀟 🀠 🀡
        🀇 🀈 🀉 🀊 🀋 🀌 🀍 🀎 🀏 
        🀀 🀁 🀂 🀃
        🀆 🀅 🀄
    """.split()

    TILES = """
        1s 2s 3s 4s 5s 6s 7s 8s 9s
        1p 2p 3p 4p 5p 6p 7p 8p 9p
        1m 2m 3m 4m 5m 6m 7m 8m 9m
        ew sw ww nw
        wd gd rd
    """.split()

    def asdata(self, convert = None):
        return self.TILES[self // 4] + str(self % 4)
        
class Player(Data):
    pass    

class Round(Data):
    pass

class Meld(Data):
    @classmethod
    def decode(Meld, data):
        data = int(data)
        meld = Meld()
        meld.fromPlayer = data & 0x3
        if data & 0x4:
            meld.decodeChi(data)
        elif data & 0x18:
            meld.decodePon(data)
        elif data & 0x20:
            meld.decodeNuki(data)
        else:
            meld.decodeKan(data)
        return meld

    def decodeChi(self, data):
        self.type = "chi"
        t0, t1, t2 = (data >> 3) & 0x3, (data >> 5) & 0x3, (data >> 7) & 0x3
        baseAndCalled = data >> 10
        self.called = baseAndCalled % 3
        base = baseAndCalled // 3
        base = (base // 7) * 9 + base % 7
        self.tiles = Tile(t0 + 4 * (base + 0)), Tile(t1 + 4 * (base + 1)), Tile(t2 + 4 * (base + 2))
    
    def decodePon(self, data):
        t4 = (data >> 5) & 0x3
        t0, t1, t2 = ((1,2,3),(0,2,3),(0,1,3),(0,1,2))[t4]
        baseAndCalled = data >> 9
        self.called = baseAndCalled % 3
        base = baseAndCalled // 3
        if data & 0x8:
            self.type = "pon"
            self.tiles = Tile(t0 + 4 * base), Tile(t1 + 4 * base), Tile(t2 + 4 * base)
        else:
            self.type = "chakan"
            self.tiles = Tile(t0 + 4 * base), Tile(t1 + 4 * base), Tile(t2 + 4 * base), Tile(t4 + 4 * base)
    
    def decodeKan(self, data):
        baseAndCalled = data >> 8
        if self.fromPlayer:
            self.called = baseAndCalled % 4
        else:
            del self.fromPlayer
        base = baseAndCalled // 4
        self.type = "kan"
        self.tiles = Tile(4 * base), Tile(1 + 4 * base), Tile(2 + 4 * base), Tile(3 + 4 * base)

    def decodeNuki(self, data):
        del self.fromPlayer
        self.type = "nuki"
        self.tiles = Tile(data >> 8)

class Event(Data):
    def __init__(self, events):
        events.append(self)
        self.type = type(self).__name__

class Dora(Event):
    pass

class Draw(Event):
    pass

class Discard(Event):
    pass

class Call(Event):
    pass

class Riichi(Event):
    pass

class Agari(Data):
    pass

class Game(Data):
    RANKS = "新人,9級,8級,7級,6級,5級,4級,3級,2級,1級,初段,二段,三段,四段,五段,六段,七段,八段,九段,十段".split(",")
    NAMES = "n0,n1,n2,n3".split(",")
    HANDS = "hai0,hai1,hai2,hai3".split(",")
    ROUND_NAMES = "東1,東2,東3,東4,南1,南2,南3,南4,西1,西2,西3,西4,北1,北2,北3,北4".split(",")
    YAKU = """
        tsumo           riichi          ippatsu         chankan 
        rinshan         haitei          houtei          pinfu   
        tanyao          ippeiko         fanpai0         fanpai1 
        fanpai2         fanpai3         fanpai4         fanpai5 
        fanpai6         fanpai7         yakuhai0        yakuhai1 
        yakuhai2        daburi          chiitoi         chanta
        itsuu           sanshokudoujin  sanshokudou     sankantsu
        toitoi          sanankou        shousangen      honrouto
        ryanpeikou      junchan         honitsu         chinitsu
        renhou          tenhou          chihou          daisangen
        suuankou        suuankou        tsuiisou        ryuuiisou
        chinrouto       chuurenpooto    chuurenpooto    kokushi
        kokushi         daisuushi       shousuushi      suukantsu
        dora            uradora         akadora
    """.split()
    LIMITS=",mangan,haneman,baiman,sanbaiman,yakuman".split(",")

    TAGS = {}
    
    def tagGO(self, tag, data):
        self.gameType = data["type"]
        self.lobby = data["lobby"]

    def tagUN(self, tag, data):
        if "dan" in data:
            for name in self.NAMES:
                if name in data:
                    player = Player()
                    player.name = urllib.parse.unquote(data[name])
                    self.players.append(player)
            ranks = self.decodeList(data["dan"])
            sexes = self.decodeList(data["sx"], dtype = str)
            rates = self.decodeList(data["rate"], dtype = float)
            for (player, rank, sex, rate) in zip(self.players, ranks, sexes, rates):
                player.rank = self.RANKS[rank]
                player.sex = sex
                player.rate = rate
                player.connected = True
        else:
            for (player, name) in zip(self.players, self.NAMES):
                if name in data:
                    player.connected = True
    
    def tagBYE(self, tag, data):
        self.players[int(data["who"])].connected = False

    def tagINIT(self, tag, data):
        self.round = Round()
        self.rounds.append(self.round)
        name, combo, riichi, d0, d1, dora = self.decodeList(data["seed"])
        self.round.round = self.ROUND_NAMES[name], combo, riichi
        self.round.hands = tuple(self.decodeList(data[hand], Tile) for hand in self.HANDS if hand in data and data[hand])
        self.round.dealer = int(data["oya"])
        self.round.events = []
        self.round.agari = []
        Dora(self.round.events).tile = Tile(dora)

    def tagN(self, tag, data):
        call = Call(self.round.events)
        call.meld = Meld.decode(data["m"])
        call.player = int(data["who"])

    def tagTAIKYOKU(self, tag, data):
        pass

    def tagDORA(self, tag, data):
        Dora(self.round.events).tile = int(data["hai"])

    def tagAGARI(self, tag, data):
        agari = Agari()
        self.round.agari.append(agari)
        agari.type = "RON" if data["fromWho"] != data["who"] else "TSUMO"
        agari.player = int(data["who"])
        agari.hand = self.decodeList(data["hai"], Tile)
        
        agari.fu, agari.points, limit = self.decodeList(data["ten"])
        if limit:
            agari.limit = self.LIMITS[limit]
        agari.dora = self.decodeList(data["doraHai"], Tile)
        agari.machi = self.decodeList(data["machi"], Tile)
        if "m" in data:
            agari.melds = self.decodeList(data["m"], Meld.decode)
            agari.closed = all(not hasattr(meld, "fromPlayer") for meld in agari.melds)
        else:
            agari.closed = True
        if "dorahaiUra" in data:
            agari.uradora = self.decodeList(data["uradoraHai"], Tile)
        if agari.type == "RON":
            agari.fromPlayer = int(data["fromWho"])
        if "yaku" in data:
            yakuList = self.decodeList(data["yaku"])
            agari.yaku = dict((self.YAKU[yaku],han) for yaku,han in zip(yakuList[::2], yakuList[1::2]))
        elif "yakuman" in data:
            agari.yakuman = tuple(self.YAKU[yaku] for yaku in self.decodeList(data["yakuman"]))

    @staticmethod
    def default(self, tag, data):
        if tag[0] in "DEFG":
            discard = Discard(self.round.events)
            discard.tile = Tile(tag[1:])
            discard.player = ord(tag[0]) - ord("D")
            discard.connected = self.players[discard.player].connected
        elif tag[0] in "TUVW":
            draw = Draw(self.round.events)
            draw.tile = Tile(tag[1:])
            draw.player = ord(tag[0]) - ord("T")
        else:
            pass

    @staticmethod
    def decodeList(list, dtype = int):
        return tuple(dtype(i) for i in list.split(","))

    def decode(self, log):
        events = etree.parse(log).getroot()
        self.rounds = []
        self.players = []
        for event in events:
            self.TAGS.get(event.tag, self.default)(self, event.tag, event.attrib)
        del self.round

for key in Game.__dict__:
    if key.startswith('tag'):
        Game.TAGS[key[3:]] = getattr(Game, key)

if __name__=='__main__':
    import yaml
    import sys
    for path in sys.argv[1:]:
        game = Game()
        game.decode(open(path))
        yaml.dump(game.asdata(), sys.stdout, default_flow_style=False, allow_unicode=True)
