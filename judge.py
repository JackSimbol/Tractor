import os
import random
import sys
import numpy as np
import json
from collections import Counter

cardscale = ['A','2','3','4','5','6','7','8','9','0','J','Q','K']
suitset = ['h','d','s','c']
Major = ['jo', 'Jo']
pointorder = ['3','4','5','6','7','8','9','0','J','Q','K','A','2']
get_score = 0 # 闲家得分
###############################################################
# 牌面表示：数字
# h:红桃 d:方片 s:黑桃 c:草花 
# (0-h1 1-d1 2-s1 3-c1) (4-h2 5-d2 6-s2 7-c2) ... 52-joker 53-Joker (54-h1 55-d1 56-s1 57-c1) ... 106-joker 107-Joker
# 请注意：10记为0
# 共2副108张
###############################################################
def num2Poker(num): # num: int-[0,107]
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

# 确定主牌
def setMajor(major, level):
    global Major
    if major != 'n': # 非无主
        Major = [major+point for point in cardscale if point != level] + [suit + level for suit in suitset if suit != major] + [major + level] + Major
    else: # 无主
        Major = [suit + level for suit in suitset] + Major
    pointorder.remove(level)
###############################################################
# 报错模块
# 报错类型：
# INVALID_POKERID 数字不在0~107中
# NOT_YOUR_POKER 打出的牌不是自己的牌
# INVALID_POKERTYPE 非法牌型
# ILLEGAL_MOVE 错误行动（出牌、报主、反主）
###############################################################
errored = [None for i in range(4)]

def setError(player, reason): # player: int-[0,3] reason: str
    if player == -1:
        raise ValueError("SYSTEM_ERROR")
    if errored[player] is None:
        errored[player] = reason
    endingScores = {}
    for i in range(4):
        if i == player:
            endingScores[str(i)] = -3 # 出错会被额外扣分
        elif i == (player + 2) % 4:
            endingScores[str(i)] = 0
        else:
            endingScores[str(i)] = 1

    print(json.dumps({
        "command": "finish",
        "content": endingScores,
        "display": {
            "currplayer": player,
            "score": endingScores,
            "error": errored
        }
    }))
    exit(0)

###############################################################
# 牌型鉴定模块
# 牌型（除甩牌外）
# 单牌 1张任意
# 对子 2张相同花色相同数字
# 连对（拖拉机）大小上连续
###############################################################

# return: pokertype(str)
def checkPokerType(poker, currplayer, level): #poker: list[int]
    poker = [num2Poker(p) for p in poker]
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
                setError(currplayer, "INVALID_POKERTYPE")
            pointpos.append(pointorder.index(k[1])) # 点数在大小上连续
        pointpos.sort()
        for i in range(len(pointpos)-1):
            if pointpos[i+1] - pointpos[i] != 1:
                return "suspect"
        return "tractor" # 说明是拖拉机
    
    return "suspect"

# 甩牌判定功能函数
# return: ExistBigger(True/False)
# 给定一组常规牌型，鉴定其他三家是否有同花色的更大牌型
def checkBigger(poker, own, currplayer, level, major):
# poker: 给定牌型 list
# own: 各家持牌 list
    tyPoker = checkPokerType(poker, currplayer, level)
    poker = [num2Poker(p) for p in poker]
    assert tyPoker != "suspect", "Type 'throw' should contain common types"
    own_pok = [[num2Poker(num) for num in hold] for hold in own]
    if poker[0] in Major: # 主牌型应用主牌压
        for i in range(own_pok):
            if i == currplayer:
                continue
            hold = own_pok[i]
            major_pok = [pok for pok in hold if pok in Major]
            count = Counter(major_pok)
            if len(poker) <= 2:
                if poker[0][1] == level and poker[0][0] != major: # 含有副级牌要单算
                    if major == 'n': # 无主
                        for k,v in count.items(): 
                            if (k == 'jo' or k == 'Jo') and v >= len(poker):
                                return True
                    else:
                        for k,v in count.items():
                            if (k == 'jo' or k == 'Jo' or k == major + level) and v >= len(poker):
                                return True
                else: 
                    for k,v in count.items():
                        if Major.index(k) > Major.index(poker[0]) and v >= len(poker):
                            return True
            else: # 拖拉机
                if "jo" in poker: # 必定是大小王连对
                    return False # 不可能被压
                if len(poker) == 4 and "jo" in count.keys() and "Jo" in count.keys():
                    if count["jo"] == 2 and count["Jo"] == 2: # 大小王连对必压
                        return True
                pos = []
                for k, v in count.items():
                    if v == 2:
                        if k != 'jo' and k != 'Jo' and k[1] != level and pointorder.index(k[1]) > pointorder.index(poker[-1][1]): # 大小王和级牌当然不会参与拖拉机
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
                                return True
                        elif suc_flag:
                            tmp = 0
                            suc_flag = False
    else: # 副牌甩牌
        suit = poker[0][0]
        for hold in own_pok:
            suit_pok = [pok for pok in hold if pok[0] == suit and pok[1] != level]
            count = Counter(suit_pok)
            if len(poker) <= 2:
                for k, v in count.items():
                    if pointorder.index(k[1]) > pointorder.index(poker[0][1]) and v >= len(poker):
                        return True
            else:
                pos = []
                for k, v in count.items():
                    if v == 2:
                        if pointorder.index(k[1]) > pointorder.index(poker[-1][1]):
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
                                return True
                        elif suc_flag:
                            tmp = 0
                            suc_flag = False

    return False

# 甩牌是否可行
# return: poker(最终实际出牌:list[str])、ilcnt(非法牌张数)
# 如果甩牌成功，返回的是对甩牌的拆分(list[list])
def checkThrow(poker, own, currplayer, level, major, check=False):
# poker: 甩牌牌型 list[int]
# own: 各家持牌 list
# level & major: 级牌、主花色
    ilcnt = 0
    pok = [num2Poker(p) for p in poker]
    outpok = []
    failpok = []
    count = Counter(pok)
    if check:
        if list(count.keys())[0] in Major: # 如果是主牌甩牌
            for p in count.keys():
                if p not in Major:
                    setError(currplayer, "INVALID_POKERTYPE")
        else: # 是副牌
            suit = list(count.keys())[0][0] # 花色相同
            for k in count.keys():
                if k[0] != suit:
                    setError(currplayer, "INVALID_POKERTYPE")
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

    if check:
        for poktype in outpok:
            if checkBigger(poktype, own, currplayer, level, major): # 甩牌失败
                ilcnt += len(poktype)
                failpok.append(poktype)
        
    if ilcnt > 0:
        finalpok = []
        kmin = ""
        for poktype in failpok:
            getmark = poktype[-1] 
            if kmin == "":
                finalpok = poktype
                kmin = getmark
            elif kmin in Major: # 主牌甩牌
                if Major.index(getmark) < Major.index(kmin):
                    finalpok = poktype
                    kmin = getmark
            else: # 副牌甩牌
                if pointorder.index(getmark[1]) < pointorder.index(kmin[1]):
                    finalpok = poktype
                    kmin = getmark
    else: 
        finalpok = outpok

    return finalpok, ilcnt 

###############################################################
# 发牌决定模块
# 先确定好发给每个人的25张牌，再进行逐一发牌
###############################################################

def initGame(full_input):
    seedRandom = str(random.randint(0, 2147483647))

    if "initdata" not in full_input:
        full_input["initdata"] = {}
    try:
        full_input["initdata"] = json.loads(full_input["initdata"])
    except Exception:
        pass
    if type(full_input["initdata"]) is not dict:
        full_input["initdata"] = {}

    if "seed" in full_input["initdata"]:
        seedRandom = full_input["initdata"]["seed"] 
    
    random.seed(seedRandom)
    if "allocation" in full_input["initdata"]:
        allocation = full_input["initdata"]["allocation"]
    else: # 产生大家各自有什么牌
        allo = [i for i in range(108)]
        random.shuffle(allo)
        allocation = [allo[8:33], allo[33:58], allo[58:83], allo[83:108]]

    if "publiccard" in full_input["initdata"]:
        publiccard = full_input["initdata"]["publiccard"]
    else:
        publiccard = allo[0:8]
    
    return full_input, seedRandom, allocation, publiccard

###############################################################
# 报主和反主模块
# 接收每回合发牌的报主和反主信息
# 类似于地主和叫分，主花色和庄家会作为常规信息单独提供给玩家
###############################################################

# return Banking
def checkBanker(repo, level, currplayer, banking): 
# repo: int(player's response) 
# level: str(current level) 
# currplayer: int(current playerid)
# banking: dict_object (called, snatched, major, banker)
    newbanking = banking
    if len(repo) == 1: # 单张报主
        if banking["called"] != -1: # 已报过主
            setError(currplayer, "ILLEGAL_MOVE")
        poker = num2Poker(repo[0])
        if poker[1] != level: # 不是级牌
            setError(currplayer, "ILLEGAL_MOVE")
        newbanking["called"] = currplayer
        newbanking["major"] = poker[0]
        newbanking["banker"] = currplayer
        return newbanking
    if len(repo) == 2: # 对子反主
        if banking["called"] == -1 or banking["snatched"] != -1: # 还未报主或已经反主
            setError(currplayer, "ILLEGAL_MOVE")
        poker = [num2Poker(repo[0]), num2Poker(repo[1])]
        if poker[0] != poker[1]: # 不是对子
            setError(currplayer, "ILLEGAL_MOVE")
        if poker[0][1] != level: # 不是级牌
            if poker[0] == "jo" or poker[0] == "Jo": # 是大小王
                newbanking["snatched"] = currplayer
                newbanking["major"] = "n"
                newbanking["banker"] = currplayer
                return newbanking
            setError(currplayer, "ILLEGAL_MOVE")
        newbanking["snatched"] = currplayer
        newbanking["major"] = poker[0][0]
        newbanking["banker"] = currplayer
        return newbanking

###############################################################
# 出牌裁判模块
# 包含针对常规出牌和甩牌的裁判模块
# checkLegalMove: 每名玩家行动后判定行动是否合法
# checkWinner: 一轮行动结束后找该轮最大的玩家
# * 行动前，会统一判断玩家出的牌是否在自己的手牌中（包括报主与反主）
###############################################################

# 罚分
def Punish(currplayer, banker, score):
    global get_score
    if (currplayer - banker) % 2 != 0: # 当前玩家不是庄家
        get_score -= score
    else: # 庄家罚分，加到闲家上
        get_score += score


# 检查是否有可应手牌型
# return: Exist(True/False)
def checkRes(poker, own, level): # poker: list[int]
    pok = [num2Poker(p) for p in poker]
    own_pok = [num2Poker(p) for p in own]
    if pok[0] in Major:
        major_pok = [pok for pok in own_pok if pok in Major]
        count = Counter(major_pok)
        if len(poker) <= 2:
            for v in count.values():
                if v >= len(poker):
                    return True
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
                            return True
                    elif suc_flag:
                        tmp = 0
                        suc_flag = False
    else:
        suit = pok[0][0]
        suit_pok = [pok for pok in own_pok if pok[0] == suit and pok[1] != level]
        count = Counter(suit_pok)
        if len(poker) <= 2:
            for v in count.values():
                if v >= len(poker):
                    return True
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
                            return True
                    elif suc_flag:
                        tmp = 0
                        suc_flag = False
    return False


# return outpok(The actual move if the move is legal; If illegal, report error)
def checkLegalMove(poker, level, major, currplayer, history, own, banker): # own: All players' hold before this move
# poker: list[int] player's move
# history: other players' moves in the current round: list[list]
    pok = [num2Poker(p) for p in poker]
    hist = [[num2Poker(p) for p in move] for move in history]
    outpok = pok
    if len(history) == 0: # The first move in a round
        # Player can only throw in the first round
        typoker = checkPokerType(poker, currplayer, level)
        if typoker == "suspect":
            outpok, ilcnt = checkThrow(poker, own, currplayer, level, major)
            if ilcnt > 0:
                Punish(currplayer, banker, ilcnt*10)
            outpok = [p for poktype in outpok for p in poktype] # 符合交互模式，把甩牌展开
    else:
        tyfirst = checkPokerType(history[0], currplayer,level)
        if len(poker) != len(history[0]):
            setError(currplayer, "ILLEGAL_MOVE")
        if tyfirst == "suspect": # 这里own不一样了，但是可以不需要check
            outhis, ilcnt = checkThrow(history[0], own, currplayer, level, major, check=False)
            # 甩牌不可能失败，因此只存在主牌毙或者贴牌的情形，且不可能有应手
            # 这种情况下的非法行动：贴牌不当
            # outhis是已经拆分好的牌型(list[list])
            flathis = [p for poktype in outhis for p in poktype]
            if outhis[0][0] in Major: 
                major_pok = [p for p in pok if p in Major]
                if len(major_pok) != len(poker): # 这种情况下，同花(主牌)必须已经贴完
                    major_hold = [p for p in own_pok if p in Major]
                    if len(major_pok) != len(major_hold):
                        setError(currplayer, "ILLEGAL_MOVE")
                else: #全是主牌
                    outhis.sort(key=lambda x: len(x), reverse=True) # 牌型从大到小来看
                    major_hold = [p for p in own_pok if p in Major]
                    matching = True
                    if checkPokerType(outhis[0], currplayer, level) == "tractor": # 拖拉机来喽
                        divider, _ = checkThrow(poker, [[]], currplayer, level, major, check=False)
                        divider.sort(key=lambda x: len(x), reverse=True)
                        dividcnt = [len(x) for x in divider]
                        own_divide, r = checkThrow(major_hold, [[]], currplayer, level, check=False)
                        own_divide.sort(key=lambda x: len(x), reverse=True)
                        own_cnt = [len(x) for x in own_divide]
                        for poktype in outhis: # 可以使用这种方法的原因在于同一组花色/主牌可组成的牌型数量太少，不会出现多解
                            if dividcnt[0] >= len(poktype):
                                dividcnt[0] -= len(poktype)
                                dividcnt.sort(reverse=True)
                            else:
                                matching = False
                                break
                        if not matching: # 不匹配，看手牌是否存在应手
                            res_ex = True
                            for chtype in own_cnt:
                                if own_cnt[0] >= len(chtype):
                                    own_cnt[0] -= len(chtype)
                                    own_cnt.sort(reverse=True)
                                else: 
                                    res_ex = False
                                    break
                            if res_ex: # 存在应手，说明贴牌不当
                                setError(currplayer, "ILLEGAL_MOVE")
                            else: # 存在应手，继续检查
                                pair_own = sum([len(x) for x in own_divide if len(x) >= 2])
                                pair_his = sum([len(x) for x in outhis if len(x) >= 2])
                                pair_pok = sum([len(x) for x in divider if len(x) >= 2])
                                if pair_pok < min(pair_own, pair_his):
                                    setError(currplayer, "ILLEGAL_MOVE")
            else:
                suit = hist[0][0][0]
                suit_pok = [p for p in pok if p not in Major and p[0] == suit]
                if len(suit_pok) != len(poker): # 这种情况下，同花(主牌)必须已经贴完
                    suit_hold = [p for p in own_pok if p not in Major and p[0] == suit]
                    if len(suit_pok) != len(suit_hold):
                        setError(currplayer, "ILLEGAL_MOVE")
                else: 
                    outhis.sort(key=lambda x: len(x), reverse=True) # 牌型从大到小来看
                    suit_hold = [p for p in own_pok if p not in Major and p[0] == suit]
                    matching = True
                    if checkPokerType(outhis[0], currplayer, level) == "tractor": # 拖拉机来喽
                        divider, _ = checkThrow(poker, [[]], currplayer, level, major, check=False)
                        divider.sort(key=lambda x: len(x), reverse=True)
                        dividcnt = [len(x) for x in divider]
                        own_divide, r = checkThrow(major_hold, [[]], currplayer, level, check=False)
                        own_divide.sort(key=lambda x: len(x), reverse=True)
                        own_cnt = [len(x) for x in own_divide]
                        for poktype in outhis: # 可以使用这种方法的原因在于同一组花色/主牌可组成的牌型数量太少，不会出现多解
                            if dividcnt[0] >= len(poktype):
                                dividcnt[0] -= len(poktype)
                                dividcnt.sort(reverse=True)
                            else:
                                matching = False
                                break
                        if not matching: # 不匹配，看手牌是否存在应手
                            res_ex = True
                            for chtype in own_cnt:
                                if own_cnt[0] >= len(chtype):
                                    own_cnt[0] -= len(chtype)
                                    own_cnt.sort(reverse=True)
                                else: 
                                    res_ex = False
                                    break
                            if res_ex: # 存在应手，说明贴牌不当
                                setError(currplayer, "ILLEGAL_MOVE")
                            else: # 存在应手，继续检查
                                pair_own = sum([len(x) for x in own_divide if len(x) >= 2])
                                pair_his = sum([len(x) for x in outhis if len(x) >= 2])
                                pair_pok = sum([len(x) for x in divider if len(x) >= 2])
                                if pair_pok < min(pair_own, pair_his):
                                    setError(currplayer, "ILLEGAL_MOVE")
                        # 到这里关于甩牌贴牌的问题基本上解决，是否存在反例还有待更详细的讨论

        else: # 常规牌型
        # 该情形下的非法行动：(1) 有可以应手的牌型但贴牌或用主牌毙 (2) 贴牌不当(有同花不贴/拖拉机有对子不贴)
            if checkRes(history[0], own[currplayer], level): #(1) 有应手但贴牌或毙
                if checkPokerType(poker, currplayer, level) != tyfirst:
                    setError(currplayer,"ILLEGAL_MOVE")
                if hist[0][0] in Major and pok[0] not in Major:
                    setError(currplayer,"ILLEGAL_MOVE")
                if hist[0][0] not in Major and (pok[0] in Major or pok[0][0] != hist[0][0][0]):
                    setError(currplayer, "ILLEGAL_MOVE") 
            elif checkPokerType(poker, currplayer, level) != tyfirst: #(2) 贴牌不当: 有同花不贴完/同花色不跟整牌型
                own_pok = [num2Poker(p) for p in own[currplayer]]
                if hist[0][0] in Major:
                    major_pok = [p for p in pok if p in Major]
                    if len(major_pok) != len(poker): # 这种情况下，同花(主牌)必须已经贴完
                        major_hold = [p for p in own_pok if p in Major]
                        if len(major_pok) != len(major_hold):
                            setError(currplayer, "ILLEGAL_MOVE")
                    else: # 完全是主牌
                        count = Counter(major_hold)
                        if tyfirst == "pair":
                            for v in count.values():
                                if v == 2:
                                    setError(currplayer, "ILLEGAL_MOVE")
                        elif tyfirst == "tractor":
                            trpairs = len(history[0])/2
                            pkcount = Counter(pok)
                            pkpairs = 0
                            hdpairs = 0
                            for v in pkcount.values():
                                if v >= 2:
                                    pkpairs += 1
                            for v in count.values():
                                if v >= 2:
                                    hdpairs += 1
                            if pkpairs < trpairs and pkpairs < hdpairs: # 并不是所有对子都用上了
                                setError(currplayer, "ILLEGAL_MOVE")

                else: 
                    suit = hist[0][0][0]
                    suit_pok = [p for p in pok if p[0] == suit]
                    suit_hold = [p for p in own_pok if p[0] == suit and p not in Major]
                    if len(suit_pok) != len(poker):    
                        if len(suit_pok) != len(suit_hold):
                            setError(currplayer, "ILLEGAL_MOVE")
                    else: # 完全是同种花色
                        count = Counter(suit_hold)
                        if tyfirst == "pair":
                            for v in count.values():
                                if v == 2:
                                    setError(currplayer, "ILLEGAL_MOVE")
                        elif tyfirst == "tractor":
                            trpairs = len(history[0])/2
                            pkcount = Counter(pok)
                            pkpairs = 0
                            hdpairs = 0
                            for v in pkcount.values():
                                if v >= 2:
                                    pkpairs += 1
                            for v in count.values():
                                if v >= 2:
                                    hdpairs += 1
                            if pkpairs < trpairs and pkpairs < hdpairs: # 并不是所有对子都用上了
                                setError(currplayer, "ILLEGAL_MOVE")
                    
    return outpok

# 在每轮最后一名玩家行动后触发判定，接收该轮历史行动及玩家本次出牌，判定胜方和分值
# 对于甩牌，盖毙只判定最大牌型的大小
# return winner(int: player ID)
def checkWinner(history, move, currplayer, level, major, banker):
    histo = history + []
    hist = [[num2Poker(p) for p in x] for x in histo]
    score = 0 
    for move in hist:
        for pok in move:
            if pok[1] == "5":
                score += 5
            elif pok[1] == "0" or pok[1] == "K":
                score += 10
    win_seq = 0 # 获胜方在本轮行动中的顺位，默认为0
    win_move = hist[0] # 获胜方的出牌，默认为首次出牌
    tyfirst = checkPokerType(history[0], currplayer, level)
    if tyfirst == "suspect": # 甩牌
        first_parse, _ = checkThrow(history[0], [[]], currplayer, level, major, check=False)
        first_parse.sort(key=lambda x: len(x), reverse=True)
        for i in range(1,4):
            move_parse, r = checkThrow(history[i], [[]], currplayer, level, major, check=False)
            move_parse.sort(key=lambda x: len(x), reverse=True)
            move_cnt = [len(x) for x in move_parse]
            matching = True
            for poktype in first_parse: # 杀毙的前提是牌型相同
                if move_cnt[0] >= len(poktype):
                    move_cnt[0] -= poktype
                    move_cnt.sort(reverse=True)
                else:
                    matching = False
                    break
            if not matching:
                continue
            if hist[i][0] not in Major: # 副牌压主牌，算了吧
                continue
            if win_move[0] not in Major and hist[i][0] in Major: # 主牌压副牌，必须的
                win_move = hist[i]
                win_seq = i
            # 两步判断后，只剩下hist[i]和win_move都是主牌的情况
            elif len(first_parse[0]) >= 4: # 有拖拉机再叫我checkThrow来
                if major == 'n': # 如果这里无主，拖拉机只可能是对大小王，不可能有盖毙
                    continue
                win_parse, s = checkThrow(history[win_seq], [[]], currplayer, level, major, check=False)
                win_parse.sort(key=lambda x: len(x), reverse=True)
                if Major.index(win_parse[0][-1]) < Major.index(move_parse[0][-1]):
                    win_move = hist[i]
                    win_seq = i
            else: 
                step = len(first_parse[0])
                win_count = Counter(win_move)
                win_max = 0
                for k,v in win_count.items():
                    if v >= step and Major.index(k) >= win_max: # 这里可以放心地这么做，因为是何种花色的副2不会影响对比的结果
                        win_max = Major.index(k)
                move_count = Counter(hist[i])
                move_max = 0
                for k,v in move_count.items():
                    if v >= step and Major.index(k) >= move_max:
                        move_max = Major.index(k)
                if major == 'n': # 无主
                    if Major[win_max][1] == level:
                        if Major[move_max] == 'jo' or Major[move_max] == 'Jo':
                            win_move = hist[i]
                            win_seq = i
                    elif Major.index(move_max) > Major.index(win_max):
                        win_move = hist[i]
                        win_seq = i
                elif Major[win_max][1] == level and Major[win_max][0] != major:
                    if (Major[move_max][0] == major and Major[move_max][1] == level) or Major[move_max] == "jo" or Major[move_max] == "Jo":
                        win_move = hist[i]
                        win_seq = i
                elif Major.index(win_max) < Major.index(move_max):
                    win_move = hist[i]
                    win_seq = i

    else: # 常规牌型
        #print("Common: Normal")
        for i in range(1, 4):
            if checkPokerType(history[i], currplayer, level) != tyfirst: # 牌型不对
                continue
            #print("check: Normal")
            if (hist[0][0] in Major and hist[i][0] not in Major) or (hist[0][0] not in Major and (hist[i][0] not in Major and hist[i][0][0] != hist[0][0][0])):
            # 花色不对，贴
                continue
            elif win_move[0] in Major: # 主牌不会被主牌杀，且该分支内应手均为主牌
                if hist[i][0] not in Major: # 副牌就不用看了
                    continue
                #print("here")
                if major == 'n':
                    if win_move[-1][1] == level:
                        if hist[i][-1] == 'jo' or hist[i][-1] == 'Jo': # 目前胜牌是级牌，只有大小王能压
                            win_move = hist[i]
                            win_seq = i
                    elif Major.index(hist[i][-1]) > Major.index(win_move[-1]):
                        win_move = hist[i]
                        win_seq = i
                else:
                    if win_move[-1][0] != major and win_move[-1][1] == level:
                        if (hist[i][-1][0] == major and hist[i][-1][1] == level) or hist[i][-1] == 'jo' or hist[i][-1] == 'Jo':
                            win_move = hist[i]
                            win_seq = i
                    elif Major.index(hist[i][-1]) > Major.index(win_move[-1]):
                        win_move = hist[i]
                        win_seq = i
            else: # 副牌存在被主牌压的情况
                if hist[i][0] in Major: # 主牌，正确牌型，必压
                    win_move = hist[i]
                    win_seq = i
                elif pointorder.index(win_move[0][-1]) < pointorder.index(hist[i][0][-1]):
                    win_move = hist[i]
                    win_seq = i
    # 找到获胜方，加分
    win_id = (currplayer - 3 + win_seq) % 4
    Reward(score, win_id, banker)

    return win_id


def Reward(score, currplayer, banker):
    global get_score
    if (currplayer - banker) % 2 != 0: # 非庄家得分
        get_score += score

# return endingScores(dict)
def EndGame(banker, score):
    endingScores = {}
    bankers = [banker, (banker + 2) % 4]
    if score <= 0: # 大光，庄家得3分
        for i in range(4):
            if i in bankers:
                endingScores[str(i)] = 3
            else: 
                endingScores[str(i)] = 0
    elif score < 40: # 小光，庄家得2分
        for i in range(4):
            if i in bankers:
                endingScores[str(i)] = 2
            else:
                endingScores[str(i)] = 0
    elif score < 80: # 庄家得1分
        for i in range(4):
            if i in bankers:
                endingScores[str(i)] = 1
            else:
                endingScores[str(i)] = 0
    elif score < 120: # 闲家得1分
        for i in range(4):
            if i in bankers:
                endingScores[str(i)] = 0
            else:
                endingScores[str(i)] = 1
    elif score < 160: # 闲家得2分
        for i in range(4):
            if i in bankers:
                endingScores[str(i)] = 0
            else:
                endingScores[str(i)] = 2
    else: 
        for i in range(4):
            if i in bankers:
                endingScores[str(i)] = 0
            else:
                endingScores[str(i)] = 3
    
    return endingScores



# initdata里包含了庄家、牌型、级牌
# global里包含了主花色、级牌、庄家（覆盖）、报主情况
def main(full_input):
    global get_score
    printContent = {}
    globalInfo = {} # 未确定主花色前为空
    lenLog = len(full_input["log"])
    curr_alloc = [[], [], [], []]
    currplayer = -1
    try:
        if lenLog == 0: # 刚开局
            full_input, seedRandom, allocation, publiccard = initGame(full_input)
            initdata = {}
            initdata["allocation"] = allocation
            initdata["seed"] = seedRandom
            initdata["publiccard"] = publiccard
            if "level" not in full_input["initdata"].keys():
                initdata["level"] = "2"
            else:
                initdata["level"] = full_input["initdata"]["level"]

            globalInfo["level"] = initdata["level"]
            #第一轮有机会写入initdata
            if "banker" not in full_input["initdata"]: # 没有规定摸牌方
                first = 0
            else:
                first = full_input["initdata"]["banker"]
                initdata["banker"] = first

            printContent["stage"] = "deal"
            printContent["deliver"] = [allocation[first][0]]
            
            curr_alloc[first].append(allocation[first][0])

            banking = {
                "called": -1,
                "snatched": -1,
                "major": "",
                "banker": -1
            } # 初始化banking
            globalInfo["banking"] = banking

            printContent["global"] = globalInfo

            print(json.dumps({
                "command": "request",
                "content": {
                    str(first): printContent
                },
                "display": { 
                    "event": {
                        "currplayer": -1,
                        "action": "init"
                    },
                    "deliver": {
                        "player": first,
                        "poker": printContent["deliver"],
                    },
                    "publiccard": publiccard,
                    "level": initdata["level"]
                },
                "initdata": initdata
            }))

        elif lenLog <= 200: # 仍在发牌中，回合199是该阶段玩家最后一次反馈（lenLog = 200）
            for i in range(lenLog): # 恢复发牌
                if i % 2 == 0: # 裁判回合
                    turnlog = full_input["log"][i]
                    player = int(list(turnlog["output"]["content"].keys())[0])
                    curr_alloc[player].append(turnlog["output"]["content"][str(player)]["deliver"][0])

            eventpoker = []
            raw_response = full_input["log"][-1]
            currplayer = int(list(raw_response.keys())[0])
            response = raw_response[str(currplayer)]["response"]
            globalInfo = list(full_input["log"][-2]["output"]["content"].values())[0]["global"]
            banking = globalInfo["banking"] # 上回合发出的banking
            level = full_input["initdata"]["level"]
            repo = response # 这里有所改动，若玩家报主只需要发送报牌，若不报发送空列表[]即可
            if len(repo) > 0:
                for poker in repo:
                    if poker not in curr_alloc[currplayer]:
                        setError(currplayer, "NOT_YOUR_POKER")
                eventpoker = repo
                new_ = True
                newbanking = checkBanker(repo, level, currplayer, banking)
            else: # 不报就不管
                eventpoker = []
                new_ = False
                newbanking = banking
        
            if lenLog < 200: # 给下一名玩家发牌
                nextplayer = (currplayer + 1) % 4
                allocation = full_input["initdata"]["allocation"]
                printContent["stage"] = "deal"
                printContent["deliver"] = [allocation[nextplayer][lenLog // 8]]
                globalInfo["banking"] = newbanking
                printContent["global"] = globalInfo
                
                printAll = {
                    "command": "request",
                    "content": {
                        str(nextplayer): printContent
                    },
                    "display":{
                        "event": {
                            "currplayer": currplayer,
                            "action": "deal",
                            "poker": eventpoker
                        },
                        "deliver": {
                            "player": nextplayer,
                            "poker": printContent["deliver"]
                        },
                        "publiccard": full_input["initdata"]["publiccard"],
                    }
                }
                if new_:
                    printAll["display"]["banking"] = newbanking
                print(json.dumps(printAll))
        
            else: # 发牌的最后一轮，要确定庄家，下回合盖底牌
                seedRandom = full_input["initdata"]["seed"]
                random.seed(seedRandom)
                if newbanking["banker"] == -1:
                    new_ = True
                    newbanking["banker"] = random.randint(0, 3)
                if newbanking["major"] == "":
                    newbanking["banker"] = suitset[random.randint(0, 3)]
                globalInfo["banking"] = newbanking
                printContent["stage"] = "cover"
                printContent["deliver"] = full_input["initdata"]["publiccard"]
                printContent["global"] = globalInfo
                printAll = {
                    "command": "request",
                    "content": {
                        str(newbanking["banker"]): printContent
                    },
                    "display": {
                        "event": {
                            "currplayer": currplayer,
                            "action": "deal",
                            "poker": eventpoker
                        },
                        "deliver": {
                            "player": newbanking["banker"],
                            "poker": printContent["deliver"],
                            "banking": newbanking
                        },
                        "publiccard": full_input["initdata"]["publiccard"],
                    }
                }
                if new_:
                    printAll["display"]["banking"] = newbanking
                print(json.dumps(printAll))
        
        elif lenLog == 202: # 第101回合，庄家返回盖底牌
            last_res = full_input["log"][-1]
            allocation = full_input["initdata"]["allocation"]
            currplayer = int(list(last_res.keys())[0])
            globalInfo = list(full_input["log"][-2]["output"]["content"].values())[0]["global"]
            global_banker = globalInfo["banking"]["banker"]
            old_publiccard = full_input["initdata"]["publiccard"]
            banking = globalInfo["banking"]
            if currplayer != global_banker: # 你的庄家在哪里？让他上前来！
                setError(currplayer, "NOT_YOUR_TURN")
            response = last_res[str(currplayer)]["response"]
            if type(response) is not list:
                 setError(currplayer, "INVALID_FORMAT")
            big_hold = old_publiccard + allocation[currplayer]
            for pok in response:
                if pok not in big_hold:
                    setError(currplayer, "NOT_YOUR_POKER")
                big_hold.remove(pok)
            
            new_alloc = allocation
            new_alloc[currplayer] = big_hold

            # 仍然给庄家发request
            printContent["stage"] = "play"
            printContent["history"] = [[],[], currplayer, currplayer]
            globalInfo["total_score"] = 0
            printContent["global"] = globalInfo
            print(json.dumps({
                "command": "request",
                "content": {
                    str(currplayer): printContent
                },
                "display": {
                    "event": {
                        "currplayer": currplayer,
                        "action": "cover",
                        "poker": response
                    },
                    "publiccard": response,
                } 
            }))

        else: # 正式出牌（101回合开始, lenLog=204）
            old_alloc = full_input["initdata"]["allocation"]
            globalInfo = list(full_input["log"][-2]["output"]["content"].values())[0]["global"]
            banker = globalInfo["banking"]["banker"]
            major = globalInfo["banking"]["major"]
            setMajor(major, full_input["initdata"]["level"])
            old_publiccard = full_input["initdata"]["publiccard"]
            new_publiccard = full_input["log"][201][str(banker)]["response"]
            big_hold = old_alloc[banker] + old_publiccard
            old_score = globalInfo["total_score"]
            for pok in new_publiccard:
                big_hold.remove(pok)
            new_alloc = old_alloc + []
            new_alloc[banker] = big_hold
            for turn_id in range(203, lenLog - 2, 2): # 还原本轮手牌（刚刚接收到的一回合信息不处理）
                response = full_input["log"][turn_id]
                player = int(list(response.keys())[0])
                move = response[str(player)]["response"]
                for pok in move:
                    new_alloc[player].remove(pok)
            
            #print("recover: Normal")

            latest_response = full_input["log"][-1]
            currplayer = int(list(latest_response.keys())[0])
            curr_move = latest_response[str(currplayer)]["response"]
            latest_request = full_input["log"][-2]
            history = list(latest_request["output"]["content"].values())[0]["history"]
            for pok in curr_move:
                if pok not in new_alloc[currplayer]:
                    setError(currplayer, "NOT_YOUR_POKER")
            outpok = checkLegalMove(curr_move, full_input["initdata"]["level"], major, currplayer, history[1], new_alloc, banker)
            # collect history

            outid = []
            for pok in outpok:
                id = Poker2Num(pok, curr_move)
                outid.append(id)
                curr_move.remove(id)
                new_alloc[currplayer].remove(id)
            
            #print("move: Normal")

            new_history = history[1]
        
            if len(new_history) == 0:
                history[3] = currplayer
            if len(new_history) < 3:
                nextplayer = (currplayer + 1) % 4
            new_history.append(outid)
            old_history = history[0]
        
            if len(new_history) == 4: # 本回合为该轮最后一次出牌
                winner = checkWinner(history[1], outid, currplayer, full_input["initdata"]["level"], major, banker)
                nextplayer = winner
                old_history = new_history
                new_history = []
                history[2] = history[3] + 0
                history[3] = winner

                if len(new_alloc[currplayer]) == 0: # 本局结束
                    # 扣底
                    if checkPokerType(outpok, currplayer, full_input["initdata"]["level"]) != "suspect":
                        mult = len(outpok)
                    else:
                        divided, _ = checkThrow(outpok, [[]], currplayer, full_input["initdata"]["level"], major, check=False)
                        divided.sort(key=lambda x: len(x), reverse=True)
                        if len(divided[0]) >= 4:
                            mult = len(divided[0]) * 2
                        elif len(divided[0]) == 2:
                            mult = 4
                        else: 
                            mult = 2

                    publicscore = 0
                    for pok in new_publiccard: 
                        p = num2Poker(pok)
                        if p[1] == "5":
                            publicscore += 5
                        elif p[1] == "0" or p[1] == "K":
                            publicscore += 10
                    
                    Reward(publicscore*mult, winner, banker)
                    new_score = old_score + get_score

                    endingScores = EndGame(banker, new_score)
                    print(json.dumps({
                        "command": "finish",
                        "content": endingScores,
                        "display": {
                            "event": {
                                "currplayer": currplayer,
                                "action": "play",
                                "poker": outid
                            },
                            "score": endingScores
                        }
                    }))
                    exit(0)

            new_score = old_score + get_score
            globalInfo["total_score"] = new_score    
            history[0] = old_history
            history[1] = new_history
            printContent["stage"] = "play"
            printContent["history"] = history
            printContent["global"] = globalInfo

            print(json.dumps({
                "command": "request",
                "content": {
                    str(nextplayer): printContent
                },
                "display": {
                    "event": {
                        "currplayer": currplayer,
                        "action": "play",
                        "poker": outid
                    }
                }
            })) 
            #print(Major)

    except ValueError as ex:
        setError(currplayer, str(ex))


_online = os.environ.get("USER", "") == "root"
if _online:
    full_input = json.loads(input())
else:
    with open("logs.json") as fo:
        full_input = json.load(fo)
main(full_input)