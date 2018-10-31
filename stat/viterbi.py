#!/usr/bin/python

# Implementation stolen from Wikipedia (https://en.wikipedia.org/wiki/Viterbi_algorithm)
# Haha, how gangsta I am...

from math import log

def viterbi(obs, states, start_p, trans_p, emit_p):
    V = [{}]
    for st in states:
        V[0][st] = {"prob": log(start_p[st]) + log(emit_p[st].get(obs[0],0.00000001)), "prev": None}
    # Run Viterbi when t > 0
    for t in range(1, len(obs)):
        V.append({})
        for st in states:
            max_tr_prob = max(V[t-1][prev_st]["prob"]+log(trans_p[prev_st].get(st,0.0000001)) for prev_st in states)
            for prev_st in states:
                if V[t-1][prev_st]["prob"] + log(trans_p[prev_st].get(st,0.0000001)) == max_tr_prob:
                    max_prob = max_tr_prob + log(emit_p[st].get(obs[t],0.0000001))
                    V[t][st] = {"prob": max_prob, "prev": prev_st}
                    break
    opt = []
    # The highest probability
    max_prob = max(value["prob"] for value in V[-1].values())
    previous = None
    # Get most probable state and its backtrack
    for st, data in V[-1].items():
        if data["prob"] == max_prob:
            opt.append(st)
            previous = st
            break
    # Follow the backtrack till the first observation
    for t in range(len(V) - 2, -1, -1):
        opt.insert(0, V[t + 1][previous]["prev"])
        previous = V[t + 1][previous]["prev"]
    return (opt,max_prob)
