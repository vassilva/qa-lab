"""Funções partilhadas pelos passos BDD (sem passos: não regista nada no behave)."""

import time

WAIT_SECONDS = 15     # o Settlement recebe os negócios por mensagens (Kafka): a instrução aparece em instantes


def eventually(fn, what, timeout=WAIT_SECONDS):
    """Repete fn() até devolver um valor verdadeiro (consistência eventual entre sistemas)."""
    deadline, last = time.time() + timeout, None
    while time.time() < deadline:
        last = fn()
        if last:
            return last
        time.sleep(0.3)
    raise AssertionError(f"Ao fim de {timeout}s: {what} (último valor: {last})")


def instruction(context):
    assert context.trade, "Nenhum negócio foi executado neste cenário"
    tid = context.trade["trade_id"]
    rows = eventually(lambda: context.api.get(f"/api/settlement/instructions?trade_id={tid}").json(),
                      f"o Settlement não recebeu o negócio {tid}")
    assert len(rows) == 1, f"Esperada 1 instrução para {tid}, encontradas {len(rows)}"
    return rows[0]
