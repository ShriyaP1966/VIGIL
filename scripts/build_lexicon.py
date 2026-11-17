#!/usr/bin/env python3
"""Builds data/lexicon.json, the rule lexicon for the offline tactic extractor (blueprint Appendix A).

Patterns are written here as raw strings so regexes stay readable, then emitted as JSON.
`<<AGENCY>>` is a macro expanded by the extractor. All patterns are matched case-insensitively on the
normalised text; use a scoped `(?-i:...)` group where case matters (e.g. the agency acronym CBI).
Devanagari patterns avoid \\b because combining marks are not word characters.

Run:  python scripts/build_lexicon.py
"""

import json
from pathlib import Path

LEXICON_VERSION = "lexicon@1.0"
OUTPUT = Path(__file__).resolve().parent.parent / "data" / "lexicon.json"

MACROS = {
    "AGENCY": (
        r"(?-i:CBI|ED|NCB|NIA|RBI|TRAI|DOT)|central\s+bureau|enforcement\s+directorate"
        r"|narcotics(?:\s+control\s+bureau)?|customs|cyber\s*(?:crime|cell|police)|crime\s*branch"
        r"|(?:mumbai|delhi|state|local)\s+police|police(?:\s+(?:station|department|headquarters))?"
        r"|income[\s-]*tax|supreme\s+court|high\s+court|reserve\s+bank"
        r"|telecom(?:munications?)?\s+(?:department|regulatory\s+authority)|fedex|dhl|blue\s*dart|india\s+post"
        r"|electricity\s+board|(?-i:SBI|HDFC|ICICI|PNB)(?:\s+bank)?|bank"
    ),
}

# (rule id, confidence, pattern)
LABELS = {
    "AUTHORITY_IMPERSONATION": [
        ("auth_calling_from", 0.9, r"\b(?:calling|speaking)\s+(?:to\s+you\s+)?(?:from|on\s+behalf\s+of)\s+(?:the\s+)?(?:<<AGENCY>>)"),
        ("auth_i_am_from", 0.9, r"\b(?:this\s+is|i\s+am|i'm|my\s+name\s+is|main|mai|mein|hum)\b[^.\n]{0,60}?\b(?:from|of|with|at|se)\s+(?:the\s+)?(?:<<AGENCY>>)"),
        ("auth_this_is_agency", 0.85, r"\b(?:this\s+is|i\s+am|i'm)\s+(?:the\s+|an?\s+)?(?:\w+\s+){0,2}?(?:<<AGENCY>>)\b"),
        ("auth_title_name", 0.85, r"(?-i:\b(?:Officer|Inspector|Sub[- ]?Inspector|Constable|Senior\s+Officer|Agent)\s+[A-Z][a-z]+)"),
        ("auth_team_claim", 0.8, r"\b(?:from|by)\s+(?:the\s+)?(?:<<AGENCY>>)\s+(?:customer\s+care|support|helpdesk|team|department|fraud\s+(?:team|department)|security\s+team|officials?)"),
        ("auth_official_notice", 0.8, r"\b(?:government|official|legal|court|police)\s+(?:notice|order|summons)\b"),
        ("auth_hinglish_se", 0.9, r"(?:<<AGENCY>>)\s*(?:se|ka|ki|ke)\s*(?:officer|inspector|adhikari|bol|baat|call)"),
        ("auth_hinglish_main", 0.9, r"\b(?:main|mai|mein)\b[^.\n]{0,40}?(?:<<AGENCY>>)[^.\n]{0,40}?\b(?:bol\s+(?:raha|rahi)|officer|inspector)"),
        ("auth_devanagari", 0.85, r"सीबीआई|सी\.?बी\.?आई|साइबर\s*क्राइम|पुलिस\s*(?:स्टेशन|विभाग|अधिकारी)|कस्टम|नार्कोटिक्स|ट्राई|क्राइम\s*ब्रांच|अधिकारी|पोलीस|पोलिस|सायबर"),
        ("auth_badge", 0.7, r"\b(?:my|officer|employee)\s+(?:badge|id|employee)\s+(?:number|no\.?|id)\b"),
    ],
    "FALSE_ALLEGATION": [
        ("alleg_linked_crime", 0.9, r"\b(?:aadhaar|aadhar|pan|sim|mobile|phone|number|account|passport|parcel|package|courier|card)\b[^.\n]{0,60}?\b(?:linked|used|involved|registered|found|connected|misused|seized|flagged|suspicious|implicated|mentioned)\b[^.\n]{0,60}?\b(?:crime|illegal|fraud|laundering|drugs?|narcotics|terror\w*|criminal|contraband|counterfeit|trafficking|harass\w+|obscene)"),
        ("alleg_keywords", 0.85, r"\b(?:money\s+laundering|illegal\s+(?:items?|parcel|package|transactions?|activit\w+)|human\s+trafficking|narcotics(?!\s+(?:control|bureau|act))|drugs?\s+(?:were\s+)?(?:found|seized|in\s+the)|contraband|counterfeit|fake\s+passports?|terror(?:ist|ism)?\s+(?:funding|links?)|cyber\s*crime\s+case|criminal\s+(?:activity|case))\b"),
        ("alleg_case_registered", 0.85, r"\b(?:case|complaint|fir|report)\s+(?:has\s+been\s+|is\s+|was\s+|have\s+been\s+)?(?:registered|filed|lodged|booked)\s+(?:against|on|in|under)"),
        ("alleg_hinglish", 0.85, r"(?:aapke|aapka|apke|apka|tumhare)\s+(?:naam|number|aadhaar|aadhar|account|sim|parcel)\b[^.\n]{0,60}?(?:case|fir|complaint|illegal|fraud|drugs|parcel|crime|laundering)|\b(?:illegal|nashili|nasheele|dhokha|fraud)\s+(?:parcel|saman|transaction|activity|case|package)"),
        ("alleg_devanagari", 0.85, r"मनी\s*लॉन्ड्रिंग|अवैध|ड्रग्स|केस\s*दर्ज|गैरकानूनी|आपके\s*नाम\s*पर|गुन्हा\s*दाखल|बेकायदेशीर|अमली\s*पदार्थ|तुमच्या\s*नावावर"),
        ("alleg_kyc", 0.8, r"\b(?:kyc|pan|aadhaar|documents?)\s+(?:is\s+|are\s+|has\s+|have\s+)?(?:expired|pending|incomplete|not\s+(?:updated|verified)|invalid|mismatch\w*)"),
        ("alleg_parcel_held", 0.8, r"\b(?:parcel|package|shipment|consignment|courier)\b[^.\n]{0,40}?\b(?:held|stuck|seized|detained|on\s+hold|intercepted|returned|undelivered|rejected)\b|\b(?:customs\s+duty|unpaid\s+(?:duty|bill|dues)|bill\s+(?:is\s+)?(?:unpaid|overdue|pending)|dues\s+(?:are\s+)?(?:pending|outstanding|unpaid|overdue)|(?:pending|outstanding|overdue)\s+dues)\b"),
        ("alleg_suspicious_activity", 0.75, r"\bsuspicious\s+(?:activity|transactions?|login)\b|\bunauthori[sz]ed\s+(?:transactions?|access|login)\b"),
    ],
    "THREAT_INTIMIDATION": [
        ("threat_will_be", 0.9, r"\b(?:you\s+(?:will|shall|would|may)\s+be|will\s+be|going\s+to\s+be)\s+(?:arrested|jailed|detained|prosecuted|charged|sent\s+to\s+jail|taken\s+into\s+custody)"),
        ("threat_keywords", 0.9, r"\b(?:arrest\s+warrant|warrant\s+(?:has\s+been\s+|is\s+|was\s+)?(?:issued|against)|non[\s-]?bailable|digital\s+arrest|legal\s+action|criminal\s+(?:charges|proceedings)|face\s+(?:arrest|action|charges|prosecution|jail)|jail\s+(?:term|time)|imprisonment)\b"),
        ("threat_fir_police", 0.8, r"\bfir\s+(?:will\s+be|shall\s+be|is\s+being)\b|\b(?:police|team|officers?)\s+(?:will|shall)\s+(?:arrive|come|reach|raid|visit)\b"),
        ("threat_account_action", 0.85, r"\b(?:will|shall|going\s+to)\s+(?:be\s+)?(?:blocked|suspended|frozen|deactivated|disconnected|terminated|cancelled|closed|seized|confiscated|cut\s+off)\b|\b(?:permanently\s+(?:blocked|banned|disconnected)|account\s+freeze)\b"),
        ("threat_hinglish", 0.9, r"\bgiraft(?:aar|ari)\b|\bjail\s+(?:jaana|jana|bhej|ho)\b|\bwarrant\s+(?:jaari|nikla|nikal)\b|\bcase\s+(?:darj|file)\s+kar\b|\b(?:band|block|suspend)\s+ho\s+(?:jayega|jaayega|jayegi|jaaegi)\b|\b(?:band|block)\s+kar\s+(?:diya|di|diye)\s+(?:jayega|jayegi|jaayega)\b|\bkanooni\s+karyavahi\b"),
        ("threat_devanagari", 0.9, r"गिरफ्तार|गिरफ़्तार|वारंट|जेल|कानूनी\s*कार्रवाई|कार्रवाई|अटक|वॉरंट|तुरुंग|कारवाई"),
    ],
    "ISOLATION": [
        # "never share your OTP/PIN/password with anyone" is safety advice (LEGITIMATE), not isolation
        ("iso_dont_tell", 0.9, r"\b(?:do\s+not|don't|dont|never|not\s+to|cannot|can't)\s+(?:tell|inform|share|speak|talk|disclose|contact|call|discuss|mention)\b(?!\s+(?:your\s+|the\s+|any\s+)?(?:otp|pin|cvv|password|passcode|card|credentials|details))[^.\n]{0,40}?\b(?:anyone|anybody|family|lawyer|advocate|friends?|relatives?|police|colleagues?|neighbou?rs?|parents?|spouse|bank)\b"),
        ("iso_stay_on_call", 0.9, r"\b(?:stay|remain|keep)\s+(?:on\s+)?(?:the\s+)?(?:video\s+)?(?:call|line|camera|skype|whatsapp)\b|\b(?:do\s+not|don't|dont)\s+(?:disconnect|hang\s*up|cut\s+the\s+call|end\s+the\s+call|leave\s+the\s+(?:call|room|house|camera))"),
        ("iso_confidential", 0.8, r"\b(?:strictly\s+confidential|confidential\s+(?:matter|case|investigation)|secret\s+investigation|national\s+security|(?:under|in)\s+(?:digital\s+)?(?:arrest|surveillance|custody)|under\s+(?:our\s+)?surveillance)\b"),
        ("iso_hinglish", 0.9, r"\bkisi\s+(?:ko|se)\s+(?:baat\s+)?(?:mat|nahi|na)\b|\bcall\s+(?:cut|disconnect|band)\s+(?:mat|nahi)\b|\bvideo\s+call\s+(?:par|pe|per|mein)\s+(?:rahiye|bane\s+rahiye|rahein|rahna|bane\s+rahein)\b|\b(?:family|ghar\s+walon|parivar)\s+(?:ko|se)\s+(?:mat|nahi)\b|\bsurveillance\s+par\b"),
        ("iso_devanagari", 0.9, r"किसी\s*(?:को|से)\s*(?:मत|नहीं)|कॉल\s*(?:मत|न)\s*काट|कोणाला\s*(?:काही\s*)?(?:सांगू\s*नका|सांगायचे\s*नाही)|कॉल\s*कट\s*करू\s*नका|व्हिडिओ\s*कॉल\s*(?:चालू|वर)\s*ठेवा|वीडियो\s*कॉल\s*पर\s*बने\s*रहें"),
    ],
    "URGENCY": [
        ("urg_minutes", 0.9, r"\b(?:within|in|next|before)\s+(?:the\s+next\s+)?(?:\d+|an?|one|two|ten|fifteen|thirty|forty|sixty)\s*(?:minutes?|mins?)\b|\bwithin\s+(?:an?\s+)?hour\b"),
        ("urg_hours_with_demand", 0.8, r"\b(?:pay|transfer|send|deposit|verify|respond|comply|report|appear|complete|update|submit)\b[^.\n]{0,50}?\b(?:within|in|before)\s+(?:the\s+next\s+)?\d+\s*(?:hours?|hrs?)\b"),
        ("urg_time_left", 0.85, r"\b(?:only\s+)?\d+\s*(?:minutes?|mins?)\s+(?:left|remaining|more)\b|\bonly\s+(?:\d+|a\s+few)\s*(?:minutes?|mins?)\b"),
        ("urg_words", 0.85, r"\b(?:immediately|right\s+now|at\s+once|without\s+delay|urgent(?:ly)?|last\s+(?:warning|chance|notice|opportunity)|final\s+(?:warning|notice|reminder)|today\s+(?:itself|only)|(?:by|before)\s+(?:today|tonight|end\s+of\s+(?:the\s+)?day)|tonight|time\s+is\s+running\s+out|asap|expires?\s+(?:today|tonight|in)|deadline)\b"),
        ("urg_hinglish", 0.9, r"\b(?:turant|foran|jaldi\s+se|jaldi|der\s+mat|bina\s+der|aaj\s+hi|abhi\s+(?:turant|ke\s+abhi|hi))\b|\b\d+\s*(?:minute|minat|ghante|ghanta)\s*(?:ke\s+andar|mein|me)\b|\babhi\s+(?:paise|payment|transfer)\b"),
        ("urg_devanagari", 0.9, r"तुरंत|फौरन|फ़ौरन|अभी\s*के\s*अभी|जल्दी|ताबडतोब|लगेच|त्वरित|लवकरात\s*लवकर|\d+\s*(?:मिनट|मिनिटांत|मिनिटात|मिनटों)"),
    ],
    "FINANCIAL_DEMAND": [
        ("dem_pay_verb", 0.9, r"\b(?:pay|transfer|send|deposit|remit|forward|wire)\b[^.\n]{0,70}?(?:\bupi\b|\baccount\b|\ba/c\b|\bwallet\b|\bfees?\b|\bcharges?\b|\bfine\b|\bpenalty\b|\bdeposit\b|\bamount\b|\bmoney\b|\bfunds?\b|\bsecurity\b|\bclearance\b|\bprocessing\b|\bverification\b|\bduty\b|\bpayment\b|\bdues\b|₹|\brs\.?\s*\d|\b\d[\d,]{2,}\b)"),
        ("dem_amount_phrase", 0.85, r"\b(?:fees?|fine|penalty|deposit|charges?|amount|security\s+deposit|clearance\s+charges?|customs\s+duty|processing\s+fee|verification\s+(?:deposit|fee|amount)|refundable\s+deposit)\s+(?:of\s+)?(?:rs\.?|₹|inr)?\s*\d"),
        ("dem_upi_handle", 0.9, r"\b(?:pay|transfer|send|deposit|remit|forward)\b[^.\n]{0,80}?[\w.\-]{2,}@[a-z][a-z]{2,}\b"),
        ("dem_to_account", 0.85, r"\bto\s+(?:this|the\s+following|our|my|given|below)\s+(?:bank\s+)?(?:account|upi|wallet|link)\b"),
        ("dem_gift_crypto", 0.9, r"\b(?:buy|purchase|get|send)\s+(?:\w+\s+){0,3}(?:gift\s+cards?|google\s+play\s+cards?|itunes|bitcoin|crypto(?:currency)?|usdt|ethereum)\b|\bwallet\s+address\b"),
        ("dem_click_pay", 0.8, r"\b(?:click|open|visit|tap|use)\s+(?:on\s+)?(?:the\s+)?(?:following\s+|below\s+|this\s+)?(?:link|url|portal|website)\b[^.\n]{0,80}?\b(?:pay|payment|verify|update|kyc|login|refund)\b|\b(?:pay|payment)\s+(?:link|portal)\b"),
        ("dem_hinglish", 0.9, r"\b(?:paise|paisa|rupaye|rupay|rupees?|amount|raqam|fees?|jurmana)\s+(?:abhi\s+)?(?:bhejo|bhejiye|bhej\s+do|transfer|jama|dijiye|de\s+do|dena)\b|\btransfer\s+(?:kijiye|karo|kar\s+do|karein|kariye)\b|\b(?:jama|deposit)\s+(?:karo|kijiye|karwa|kariye|karein)\b|\b(?:upi|account)\s+(?:par|pe|me|mein)\s+(?:transfer|bhej|jama)"),
        ("dem_devanagari", 0.9, r"पैसे\s*(?:भेजो|भेजिए|भेजें|ट्रांसफर)|ट्रांसफर\s*(?:करो|कीजिए|करें)|जमा\s*(?:करो|कीजिए|करें|करा)|पैसे\s*(?:पाठवा|भरा)|ट्रान्सफर\s*करा|रक्कम\s*(?:पाठवा|भरा|जमा)"),
    ],
    "CREDENTIAL_REQUEST": [
        ("cred_verb_secret", 0.9, r"(?<!not\s)(?<!never\s)(?<!n't\s)(?<!dont\s)(?<!mat\s)(?<!nahi\s)\b(?:share|tell|give|send|provide|read\s+out|enter|confirm|submit|batao|bataiye|bataye|dijiye|bolo|bhejo|bhejiye)\b(?![^.\n]{0,10}\b(?:na|nahi|mat)\b)[^.\n]{0,40}?\b(?:otp|one[\s-]*time\s+password|upi\s*pin|mpin|pin|cvv|password|passcode|card\s+number|card\s+details|aadhaar\s+number|net\s*banking|login\s+(?:id|details|credentials)|security\s+code|verification\s+code|atm\s+pin)\b"),
        ("cred_secret_verb", 0.9, r"\b(?:otp|pin|cvv|password|passcode|card\s+number|card\s+details)\s+(?:batao|bataiye|bataye|share|dijiye|bhejo|bhejiye|chahiye|send|do|bolo)\b(?!\s+(?:na|nahi|mat)\b)"),
        ("cred_devanagari", 0.9, r"(?:ओटीपी|पिन|सीवीवी|पासवर्ड)\s*(?:बताओ|बताइए|बताएं|भेजो|दीजिए|सांगा|द्या|शेयर)"),
        ("cred_enter_details", 0.8, r"\b(?:enter|fill|submit|update)\s+(?:your\s+)?(?:card|bank|login|account|kyc)\s+(?:details|number|credentials|information)\b"),
    ],
    "LEGITIMATE": [
        ("legit_never_share", 0.9, r"\b(?:do\s+not|don't|dont|never|please\s+do\s+not)\s+share\s+(?:your\s+|the\s+|it\s+)?(?:\w+\s+){0,2}(?:otp|pin|pins|cvv|password|passwords|passcode|card|details|credentials|it)\b|\b(?:otp|pin|password)s?\s+(?:kisi\s+ko\s+)?(?:share\s+)?(?:na|nahi|mat)\s+(?:karein|kare|kijiye|karo|batayein|batana)\b|\bnever\s+share\b"),
        ("legit_visit_branch", 0.85, r"\b(?:visit|come\s+to|reach|go\s+to|approach)\s+(?:your\s+|the\s+|our\s+)?(?:nearest\s+|home\s+|local\s+)?(?:bank\s+)?(?:branch|station|office)\b"),
        ("legit_official_channel", 0.85, r"\b(?:call|contact|dial|use)\s+(?:our\s+|the\s+)?(?:official|toll[\s-]?free|customer\s+care|national)\s+(?:helpline|number|website|app|portal|care)\b|\b(?:official\s+(?:app|website|helpline|number|portal)|helpline\s+1930|national\s+helpline)\b"),
        ("legit_no_action", 0.85, r"\b(?:no|not)\s+(?:any\s+)?(?:action|payment|fee|fees|charges?)\s+(?:is\s+|are\s+)?(?:required|needed|necessary|payable)\b|\bno\s+payment\s+is\b|\bfree\s+of\s+charge\b"),
        ("legit_info", 0.8, r"\b(?:has\s+been|have\s+been|was)\s+(?:successfully\s+)?(?:dispatched|delivered|shipped|credited|debited|generated|processed|scheduled)\b|\b(?:card|statement|cheque\s*book|passport|order|parcel|package)\s+(?:is|has\s+been)\s+(?:ready|out\s+for\s+delivery)\b|\bout\s+for\s+delivery\b|\bfor\s+your\s+information\b|\bthank\s+you\s+for\s+(?:banking|choosing|shopping|using)\b|\bif\s+(?:this\s+was\s+)?not\s+(?:you|done\s+by\s+you),?\s+(?:call|contact|visit)"),
        ("legit_devanagari", 0.8, r"किसी\s*को\s*(?:ओटीपी|पिन)\s*(?:न|ना|नहीं)\s*(?:बताएं|बताएँ|दें)|शाखा\s*(?:में|पर)\s*(?:आएं|जाएं)|कोणाला\s*(?:ओटीपी|पिन)\s*(?:देऊ\s*नका|सांगू\s*नका)"),
    ],
    "OTHER_SUSPICIOUS": [
        ("other_prize_invest", 0.6, r"\b(?:lottery|lucky\s+draw|you\s+(?:have\s+)?won|prize\s+money|kbc|work\s+from\s+home|investment\s+(?:opportunity|scheme|plan)|guaranteed\s+returns?|double\s+your\s+money|crypto\s+investment|part[\s-]time\s+job|loan\s+approved)\b"),
        ("other_short_link", 0.6, r"\b(?:bit\.ly|tinyurl\.com|t\.co|goo\.gl|cutt\.ly)/\S+"),
    ],
}

# Ordered: the first class whose cue appears in the non-victim text wins.
INSTITUTION_CUES = [
    ("CENTRAL_AGENCY", r"(?-i:CBI|ED|NCB|NIA)|central\s+bureau|enforcement\s+directorate|narcotics|income[\s-]*tax|सीबीआई"),
    ("POLICE", r"police|cyber\s*(?:crime|cell|police)|crime\s*branch|पुलिस|पोलीस|पोलिस|साइबर|सायबर"),
    ("TELECOM", r"(?-i:TRAI|DOT)|telecom|\bsim\b|ट्राई"),
    ("COURIER_CUSTOMS", r"customs|fedex|dhl|blue\s*dart|india\s+post|courier|कस्टम"),
    ("GOVT_OTHER", r"government|ministry|supreme\s+court|high\s+court|electricity\s+board|court|municipal"),
    ("BANK", r"\bbank\b|(?-i:SBI|HDFC|ICICI|PNB|RBI)|\bkyc\b|reserve\s+bank|\bbranch\b|\bcheque\b|(?:debit|credit)\s+card|net\s*banking"),
]

# Ordered: first match wins; only consulted when a demand or credential request was detected.
PAYMENT_CUES = [
    ("GIFT_CARD", r"gift\s+cards?|google\s+play\s+card|itunes"),
    ("CRYPTO", r"bitcoin|crypto|usdt|ethereum|wallet\s+address"),
    ("UPI", r"\bupi\b|gpay|google\s+pay|phonepe|paytm|bhim|[\w.\-]{2,}@[a-z]{2,}\b"),
    ("LINK_PAYMENT", r"payment\s+link|pay(?:ment)?\s+(?:via|using|through)\s+(?:the\s+)?link|click\s+(?:on\s+)?(?:the\s+)?(?:link|url)|https?://"),
    ("BANK_TRANSFER", r"account\s*(?:number|no\.?)|\bifsc\b|\bneft\b|\brtgs\b|\bimps\b|bank\s+account|\ba/c\b|खाता"),
]


def build() -> dict:
    return {
        "version": LEXICON_VERSION,
        "note": "Generated by scripts/build_lexicon.py. Edit that script, not this file.",
        "macros": MACROS,
        "labels": {
            label: [{"id": rid, "confidence": conf, "pattern": pat} for rid, conf, pat in rules]
            for label, rules in LABELS.items()
        },
        "institution_cues": [{"class": c, "pattern": p} for c, p in INSTITUTION_CUES],
        "payment_cues": [{"channel": c, "pattern": p} for c, p in PAYMENT_CUES],
    }


def render() -> str:
    return json.dumps(build(), ensure_ascii=False, indent=1) + "\n"


if __name__ == "__main__":
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(render(), encoding="utf-8")
    print(f"Wrote {OUTPUT} ({OUTPUT.stat().st_size} bytes)")
