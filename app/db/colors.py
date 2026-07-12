DELPHI_NAMED_COLORS = {
    "clBlack": "#000000",
    "clWhite": "#FFFFFF",
    "clRed": "#FF0000",
    "clGreen": "#008000",
    "clBlue": "#0000FF",
    "clYellow": "#FFFF00",
    "clSilver": "#C0C0C0",
    "clGray": "#808080",
    "clLtGray": "#C0C0C0",
    "clDkGray": "#808080",
    "clBtnFace": "#F0F0F0",
    "clWindow": "#FFFFFF",
    "clNone": "transparent",
}


def delphi_color_to_css(value, default: str = "#FFFFFF") -> str:
    """Converte um TColor do Delphi (string '$BBGGRR', nome clXxx, ou inteiro) para '#RRGGBB'."""
    if value is None:
        return default
    s = str(value).strip()
    if not s:
        return default
    if s in DELPHI_NAMED_COLORS:
        return DELPHI_NAMED_COLORS[s]

    if s.startswith("$"):
        hex_part = s[1:]
    elif s.lstrip("-").isdigit():
        hex_part = format(int(s) & 0xFFFFFF, "06x")
    else:
        return default

    hex_part = hex_part.rjust(6, "0")[-6:]
    try:
        bb, gg, rr = hex_part[0:2], hex_part[2:4], hex_part[4:6]
        int(bb, 16), int(gg, 16), int(rr, 16)
    except ValueError:
        return default

    return f"#{rr}{gg}{bb}".lower()
