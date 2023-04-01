import json
from collections import Counter
import os

cardscale = ['A','2','3','4','5','6','7','8','9','0','J','Q','K']
suitset = ['h','d','s','c']
Major = ['jo', 'Jo']
pointorder = ['3','4','5','6','7','8','9','0','J','Q','K','A','2']

def Num2Poker(num): # num: int-[0,107]
    # Already a poker
    if type(num) is str and (num in Major or (num[0] in suitset and num[1] in cardscale)):
        return num
    # Locate in 1 single deck
    NumInDeck = num % 54
    # joker and Joker:
    if NumInDeck == 52:
        return "jo"
    if NumInDeck == 53:
        return "Jo"
    # Normal cards:
    pokernumber = cardscale[NumInDeck // 4]
    pokersuit = suitset[NumInDeck % 4]
    return pokersuit + pokernumber

def Poker2Num(poker, deck): # poker: str
    NumInDeck = -1
    if poker[0] == "j":
        NumInDeck = 52
    elif poker[0] == "J":
        NumInDeck = 53
    else:
        NumInDeck = cardscale.index(poker[1])*4 + suitset.index(poker[0])
    if NumInDeck in deck:
        return NumInDeck
    else:
        return NumInDeck + 54

def checkPokerType(poker, level): #poker: list[int]
    poker = [Num2Poker(p) for p in poker]
    if len(poker) == 1:
        return "single" #一张牌必定为单牌
    if len(poker) == 2:
        if poker[0] == poker[1]:
            return "pair" #同点数同花色才是对子
        else:
            return "suspect" #怀疑是甩牌
    if len(poker) % 2 == 0: #其他情况下只有偶数张牌可能是整牌型（连对）
    # 连对：每组两张；各组花色相同；各组点数在大小上连续(需排除大小王和级牌)
        count = Counter(poker)
        if "jo" in count.keys() and "Jo" in count.keys() and count['jo'] == 2 and count['Jo'] == 2:
            return "tractor"
        elif "jo" in count.keys() or "Jo" in count.keys(): # 排除大小王
            return "suspect"
        for v in count.values(): # 每组两张
            if v != 2:
                return "suspect"
        pointpos = []
        suit = list(count.keys())[0][0] # 花色相同
        for k in count.keys():
            if k[0] != suit or k[1] == level: # 排除级牌
                raise ValueError("INVALID INPUT POKERTYPE")
            pointpos.append(pointorder.index(k[1])) # 点数在大小上连续
        pointpos.sort()
        for i in range(len(pointpos)-1):
            if pointpos[i+1] - pointpos[i] != 1:
                return "suspect"
        return "tractor" # 说明是拖拉机
    
    return "suspect"

def setMajor(major, level):
    if major != 'n': # 非无主
        Major = [major+point for point in cardscale if point != level] + [suit + level for suit in suitset if suit != major] + [major + level] + Major
    else: # 无主
        Major = [suit + level for suit in suitset] + Major
    pointorder.remove(level)

# 检查是否有可应手牌型
# return: Exist(True/False)
def checkRes(poker, own, level): # poker: list[int]
    pok = [Num2Poker(p) for p in poker]
    own_pok = [Num2Poker(p) for p in own]
    if pok[0] in Major:
        major_pok = [pok for pok in own_pok if pok in Major]
        count = Counter(major_pok)
        if len(poker) <= 2:
            for k,v in count.items():
                if v >= len(poker):
                    if len(poker) == 1:
                        return [Poker2Num(k, own)]
                    else:
                        return [Poker2Num(k, own), Poker2Num(k,own) + 54]  
                        
        else: # 拖拉机 
            pos = []
            for k, v in count.items():
                if v == 2:
                    if k != 'jo' and k != 'Jo' and k[1] != level: # 大小王和级牌当然不会参与拖拉机
                        pos.append(pointorder.index(k[1]))
            if len(pos) >= 2:
                pos.sort()
                tmp = 0
                suc_flag = False
                for i in range(len(pos)-1):
                    if pos[i+1]-pos[i] == 1:
                        if not suc_flag:
                            tmp = 2
                            suc_flag = True
                        else:
                            tmp += 1
                        if tmp >= len(poker)/2:
                            out = []
                            for j in range(i+2):
                                out.extend([Poker2Num(pok[0][0]+cardscale[pointorder[j]], own), Poker2Num(pok[0][0]+cardscale[pointorder[j]], own)+54])
                            return out
                    elif suc_flag:
                        tmp = 0
                        suc_flag = False
    else:
        suit = pok[0][0]
        suit_pok = [pok for pok in own_pok if pok[0] == suit and pok[1] != level]
        count = Counter(suit_pok)
        if len(poker) <= 2:
            for k,v in count.items():
                if v >= len(poker):
                    if len(poker) == 1:
                        return [Poker2Num(k, own)]
                    else:
                        return [Poker2Num(k, own), Poker2Num(k,own) + 54]  
        else:
            pos = []
            for k, v in count.items():
                if v == 2:
                    pos.append(pointorder.index(k[1]))
            if len(pos) >= 2:
                pos.sort()
                tmp = 0
                suc_flag = False
                for i in range(len(pos)-1):
                    if pos[i+1]-pos[i] == 1:
                        if not suc_flag:
                            tmp = 2
                            suc_flag = True
                        else:
                            tmp += 1
                        if tmp >= len(poker)/2:
                            out = []
                            for j in range(i+2):
                                out.extend([Poker2Num(suit+cardscale[pointorder[j]], own), Poker2Num(suit+cardscale[pointorder[j]], own)+54])
                            return out
                    elif suc_flag:
                        tmp = 0
                        suc_flag = False
    return False

def parsePoker(poker, level):
# poker: 甩牌牌型 list[int]
# own: 各家持牌 list
# level & major: 级牌、主花色
    pok = [Num2Poker(p) for p in poker]
    outpok = []
    failpok = []
    count = Counter(pok)
    # 优先检查整牌型（拖拉机）
    pos = []
    tractor = []
    suit = ''
    for k, v in count.items():
        if v == 2:
            if k != 'jo' and k != 'Jo' and k[1] != level: # 大小王和级牌当然不会参与拖拉机
                pos.append(pointorder.index(k[1]))
                suit = k[0]
    if len(pos) >= 2:
        pos.sort()
        tmp = []
        suc_flag = False
        for i in range(len(pos)-1):
            if pos[i+1]-pos[i] == 1:
                if not suc_flag:
                    tmp = [suit + pointorder[pos[i]], suit + pointorder[pos[i]], suit + pointorder[pos[i+1]], suit + pointorder[pos[i+1]]]
                    del count[suit + pointorder[pos[i]]]
                    del count[suit + pointorder[pos[i+1]]] # 已计入拖拉机的，从牌组中删去
                    suc_flag = True
                else:
                    tmp.extend([suit + pointorder[pos[i+1]], suit + pointorder[pos[i+1]]])
                    del count[suit + pointorder[pos[i+1]]]
            elif suc_flag:
                tractor.append(tmp)
                suc_flag = False
        if suc_flag:
            tractor.append(tmp)
    # 对牌型作基础的拆分 
    for k,v in count.items(): 
        outpok.append([k for i in range(v)])
    outpok.extend(tractor)

    finalpok = outpok

    return finalpok 




##################################################################################
def call_Snatch(get_card, deck, called, snatched, level):
# get_card: new card in this turn (int)
# deck: your deck (list[int]) before getting the new card
# called & snatched: player_id, -1 if not called/snatched
# level: level
# return -> list[int]
# 本bot不报/反
    response = []
    return response

def cover_Pub(old_public, deck):
# old_public: raw publiccard (list[int])
## 直接盖回去
    return old_public

def playCard(history, deck, level):
# history: raw history (list[list[int]])
# deck: your deck (list[int])
# level: level
# major: major (str)
# return -> move(list[int])
    if len(history) == 0:
        return [deck[0]] # 首发就乱出
    poker_deck = [Num2Poker(id) for id in deck]
    standard_move = history[0]
    standard_poker = [Num2Poker(id) for id in standard_move]
    if checkPokerType(standard_move, level) != "suspect": # 不是甩牌
        response = checkRes(standard_move, deck, level)
        if response:
            return response
        else:
            if standard_poker[0] in Major:
                deck_Major = [pok for pok in poker_deck if pok in Major]
                if len(deck_Major) < len(standard_poker):
                    out = deck_Major
                    deck_nMajor = [pok for pok in poker_deck if pok not in Major]
                    for i in range(len(standard_poker) - len(deck_Major)):
                        out.append(deck_nMajor[i])
                    attach_resp = []
                    _deck = deck + []
                    for pok in out:
                        cardid = Poker2Num(pok, _deck)
                        _deck.remove(cardid)
                        attach_resp.append(cardid)
                    return attach_resp
                else: 
                    target_parse = parsePoker(deck_Major, level)
                    target_parse.sort(key=lambda x: len(x), reverse=True)
                    target_len = len(standard_poker)
                    out = []
                    for poks in target_parse:
                        if target_len == 0:
                            break
                        if len(poks) >= target_len:
                            out.extend(poks[:target_len])
                            target_len = 0
                        else:
                            out.extend(poks)
                            target_len -= len(poks)
                    resp = []
                    _deck = deck + []
                    for pok in out:
                        cardid = Poker2Num(pok, _deck)
                        _deck.remove(cardid)
                        resp.append(cardid)
                    return resp
            else:
                suit = standard_poker[0][0]
                deck_suit = [pok for pok in poker_deck if pok[0] == suit and pok[1] != level]
                if len(deck_suit) < len(standard_poker):
                    out = deck_suit
                    deck_nsuit = [pok for pok in poker_deck if pok not in deck_suit]
                    for i in range(len(standard_poker) - len(deck_suit)):
                        out.append(deck_nsuit[i])
                    attach_resp = []
                    _deck = deck + []
                    for pok in out:
                        cardid = Poker2Num(pok, _deck)
                        _deck.remove(cardid)
                        attach_resp.append(cardid)
                    return attach_resp
                else: 
                    target_parse = parsePoker(deck_suit, level)
                    target_parse.sort(key=lambda x: len(x), reverse=True)
                    target_len = len(standard_poker)
                    out = []
                    for poks in target_parse:
                        if target_len == 0:
                            break
                        if len(poks) >= target_len:
                            out.extend(poks[:target_len])
                            target_len = 0
                        else:
                            out.extend(poks)
                            target_len -= len(poks)
                    resp = []
                    _deck = deck + []
                    for pok in out:
                        cardid = Poker2Num(pok, _deck)
                        _deck.remove(cardid)
                        resp.append(cardid)
                    return resp
    else:
        if standard_poker[0] in Major:
            deck_Major = [pok for pok in poker_deck if pok in Major]
            if len(deck_Major) < len(standard_poker):
                deck_nMajor = [pok for pok in poker_deck if pok not in Major]
                out = deck_Major
                for i in range(len(standard_poker) - len(deck_Major)):
                    out.append(deck_nMajor[i])
                attach_resp = []
                _deck = deck + []
                for pok in out:
                    cardid = Poker2Num(pok, _deck)
                    _deck.remove(cardid)
                    attach_resp.append(cardid)
                return attach_resp
            else:
                deck_parse = parsePoker(deck_Major, level)
                target_parse = parsePoker(standard_move)
                deck_parse.sort(key=lambda x: len(x), reverse=True)
                target_parse.sort(key=lambda x: len(x), reverse=True)
                out = []
                for target_unit in target_parse:
                    unit_len = len(target_unit)
                    for deck_unit in deck_parse:
                        if len(deck_unit) >= unit_len:
                            out.extend(deck_unit[:unit_len])
                            unit_len = 0
                            deck_unit = deck_unit[unit_len+1:]
                            deck_parse.sort(key=lambda x: len(x), reverse=True)
                        else:
                            out.extend(deck_unit)
                            unit_len -= len(deck_unit)
                            deck_unit = []
                            deck_parse.sort(key=lambda x: len(x), reverse=True)
                    resp = []
                    _deck = deck + []
                    for pok in out:
                        cardid = Poker2Num(pok, _deck)
                        _deck.remove(cardid)
                        resp.append(cardid)
                    return resp
        else:
            suit = standard_poker[0][0]
            deck_suit = [pok for pok in poker_deck if pok[0] == suit]
            if len(deck_suit) < len(standard_poker):
                deck_nsuit = [pok for pok in poker_deck if pok not in deck_suit]
                out = deck_suit
                for i in range(len(standard_poker) - len(deck_suit)):
                    out.append(deck_nsuit[i])
                attach_resp = []
                _deck = deck + []
                for pok in out:
                    cardid = Poker2Num(pok, _deck)
                    _deck.remove(cardid)
                    attach_resp.append(cardid)
                return attach_resp
            else:
                deck_parse = parsePoker(deck_suit, level)
                target_parse = parsePoker(standard_move)
                deck_parse.sort(key=lambda x: len(x), reverse=True)
                target_parse.sort(key=lambda x: len(x), reverse=True)
                out = []
                for target_unit in target_parse:
                    unit_len = len(target_unit)
                    for deck_unit in deck_parse:
                        if len(deck_unit) >= unit_len:
                            out.extend(deck_unit[:unit_len])
                            unit_len = 0
                            deck_unit = deck_unit[unit_len+1:]
                            deck_parse.sort(key=lambda x: len(x), reverse=True)
                        else:
                            out.extend(deck_unit)
                            unit_len -= len(deck_unit)
                            deck_unit = []
                            deck_parse.sort(key=lambda x: len(x), reverse=True)
                    resp = []
                    _deck = deck + []
                    for pok in out:
                        cardid = Poker2Num(pok, _deck)
                        _deck.remove(cardid)
                        resp.append(cardid)
                    return resp

_online = os.environ.get("USER", "") == "root"
if _online:
    full_input = json.loads(input())
else:
    with open("log_forAI.json") as fo:
        full_input = json.load(fo)
hold = []
for i in range(len(full_input["requests"])-1):
    req = full_input["requests"][i]
    if req["stage"] == "deal":
        hold.extend(req["deliver"])
    elif req["stage"] == "cover":
        hold.extend(req["deliver"])
        action_cover = full_input["responses"][i]
        for id in action_cover:
            hold.remove(id)
    elif req["stage"] == "play":
        history = req["history"]
        selfid = (history[3] + len(history[1])) % 4
        if len(history[0]) != 0:
            self_move = history[0][(selfid-history[2]) % 4]
            #print(hold)
            #print(self_move)
            for id in self_move:
                hold.remove(id)
curr_request = full_input["requests"][-1]
if curr_request["stage"] == "deal":
    get_card = curr_request["deliver"][0]
    called = curr_request["global"]["banking"]["called"]
    snatched = curr_request["global"]["banking"]["snatched"]
    level = curr_request["global"]["level"]
    response = call_Snatch(get_card, hold, called, snatched, level)
elif curr_request["stage"] == "cover":
    publiccard = curr_request["deliver"]
    response = cover_Pub(publiccard, hold)
elif curr_request["stage"] == "play":
    history = curr_request["history"]
    selfid = (history[3] + len(history[1])) % 4
    if len(history[0]) != 0:
        self_move = history[0][(selfid-history[2]) % 4]
        #print(hold)
        #print(self_move)
        for id in self_move:
            hold.remove(id)
    history_curr = history[1]
    level = curr_request["global"]["level"]
    response = playCard(history_curr, hold, level)

print(json.dumps({
    "response": response
}))



