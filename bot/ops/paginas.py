"""Manipulação e interpretação de intervalos de páginas."""

from bot.ops import OpError


def parse_ranges(spec: str, total: int) -> list[list[int]]:
    """Converte especificação textual 1-based em lista de grupos de índices 0-based."""
    if total <= 0:
        raise OpError("Total de páginas deve ser maior que zero.")
    if not isinstance(spec, str):
        raise OpError("Especificação de páginas deve ser texto.")

    cleaned_spec = spec.replace(" ", "")
    if not cleaned_spec:
        raise OpError("Especificação de páginas não pode ser vazia.")

    parts = cleaned_spec.split(",")
    groups: list[list[int]] = []

    for part in parts:
        if not part:
            raise OpError("Intervalo vazio encontrado na especificação.")

        if "-" in part:
            pieces = part.split("-")
            if len(pieces) != 2:
                raise OpError(f"Formato de intervalo inválido: '{part}'.")
            left, right = pieces
            try:
                start = 1 if not left else int(left)
                end = total if not right else int(right)
            except ValueError:
                raise OpError(f"Número de página inválido em '{part}'.")
        else:
            try:
                start = end = int(part)
            except ValueError:
                raise OpError(f"Número de página inválido: '{part}'.")

        if start < 1 or end > total or start > end:
            raise OpError(
                f"Intervalo {start}-{end} inválido para documento com {total} páginas."
            )

        groups.append(list(range(start - 1, end)))

    return groups


def parse_pages(spec: str, total: int) -> list[int]:
    """Retorna lista plana de índices de páginas 0-based a partir da especificação."""
    groups = parse_ranges(spec, total)
    return [p for group in groups for p in group]
