#!/usr/bin/env python3
"""Probe fuer den Riegel: elf Aufrufe gegen die Attrappe, danach zaehlt das Protokoll der Attrappe, was ankam."""
import graph

tok = graph.token()
faelle = [("DELETE", "/groups/abc", None), ("PATCH", "/groups/abc", {"displayName": "Neu"}),
          ("PATCH", "/groups/abc", {"visibility": "Public"}), ("PATCH", "/groups/abc", {"mailNickname": "neu"}),
          ("POST", "/users/x/events/1/cancel", {}), ("POST", "/users/x/messages/1/permanentDelete", {}),
          ("POST", "/users/x/messages/1/send", {}), ("POST", "/users/x/sendMail", {"message": {}}),
          ("POST", "/users/x/events/1/accept?sendResponse=true", {}), ("POST", "/users/x/events/1/tentativelyAccept/", {}),
          ("POST", "/users/x/messages", {"subject": "x"})]
for methode, pfad, rumpf in faelle:
    try:
        graph.aufruf(tok, methode, pfad, rumpf); print(f"durch    {methode} {pfad} {sorted(rumpf or {})}")
    except graph.Gebremst:
        print(f"GEBREMST {methode} {pfad} {sorted(rumpf or {})}")
