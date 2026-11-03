"""
Settlement (liquidação) T+2.

Inspirado no pós-negociação da Euronext (Euronext Clearing → Euronext Securities → T2S):
cada negócio gera uma instrução de liquidação para a data T+2 (dois dias úteis depois
da data de negociação). O processo de fim de dia (EOD) liquida as instruções que chegaram
à data prevista e escreve um ficheiro de relatório.

Estados de uma instrução:
    PENDING   à espera da data de liquidação
    ON_HOLD   retida (hold) pelo participante; não liquida até ser libertada (release)
    SETTLED   liquidada (títulos e dinheiro trocados)

Dias úteis: segunda a sexta, exceto os dias de fecho da TARGET2:
1 de janeiro, Sexta-feira Santa, Segunda-feira de Páscoa, 1 de maio, 25 e 26 de dezembro.
"""

import csv
import os
from datetime import date, timedelta

from app.logs import LOG_DIR, get_logger
from app.model import challenge_mode

SETTLEMENT_CYCLE = 2          # T+2
EOD_DIR = os.path.join(LOG_DIR, "eod")

log = get_logger("SETTLEMENT")


# ---------------------------------------------------------------------- calendário
def easter_sunday(year: int) -> date:
    """Domingo de Páscoa (algoritmo de Meeus/Jones/Butcher, calendário gregoriano)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def target2_holidays(year: int) -> set:
    easter = easter_sunday(year)
    return {
        date(year, 1, 1),
        easter - timedelta(days=2),   # Sexta-feira Santa
        easter + timedelta(days=1),   # Segunda-feira de Páscoa
        date(year, 5, 1),
        date(year, 12, 25),
        date(year, 12, 26),
    }


def is_business_day(d: date) -> bool:
    if d.weekday() >= 5:
        return False
    if challenge_mode():
        return True               # defeito escondido: ignora os feriados TARGET2
    return d not in target2_holidays(d.year)


def add_business_days(start: date, days: int) -> date:
    d = start
    while days > 0:
        d += timedelta(days=1)
        if is_business_day(d):
            days -= 1
    return d


def next_business_day(d: date) -> date:
    return add_business_days(d, 1)


def to_date(value) -> date:
    return value if isinstance(value, date) else date.fromisoformat(str(value)[:10])


# ---------------------------------------------------------------------- serviço
class SettlementService:
    def __init__(self, database):
        self.db = database

    # data de negócio do sistema (guardada na base de dados, sobrevive a reinícios)
    def business_date(self) -> date:
        value = self.db.get_state("business_date")
        if value:
            return to_date(value)
        today = date.today()
        if not is_business_day(today):
            today = next_business_day(today)
        self.set_business_date(today)
        return today

    def set_business_date(self, d: date):
        self.db.set_state("business_date", d.isoformat())
        self.db.commit()
        log.info("Data de negócio definida para %s", d.isoformat())

    def create_instruction(self, trade) -> dict:
        trade_date = to_date(trade.trade_date)
        isd = add_business_days(trade_date, SETTLEMENT_CYCLE)
        instruction = {
            "instruction_id": "S" + trade.trade_id[1:],
            "trade_id": trade.trade_id,
            "symbol": trade.symbol,
            "qty": trade.qty,
            "amount": round(trade.qty * trade.price, 2),
            "trade_date": trade_date,
            "intended_settlement_date": isd,
            "status": "PENDING",
        }
        self.db.insert_instruction(instruction)
        log.info("Instrução %s criada para o negócio %s: %d %s, %.2f EUR, liquidação prevista %s",
                 instruction["instruction_id"], trade.trade_id, trade.qty, trade.symbol,
                 instruction["amount"], isd.isoformat())
        return instruction

    def hold(self, instruction_id) -> bool:
        return self._transition(instruction_id, "PENDING", "ON_HOLD", "retida (hold)")

    def release(self, instruction_id) -> bool:
        return self._transition(instruction_id, "ON_HOLD", "PENDING", "libertada (release)")

    def _transition(self, instruction_id, current, new, label):
        instruction = self.db.get_instruction(instruction_id)
        if instruction is None or instruction["status"] != current:
            log.warning("Instrução %s não pode ser %s (estado atual: %s)", instruction_id, label,
                        instruction["status"] if instruction else "inexistente")
            return False
        self.db.update_instruction(instruction_id, new, None)
        self.db.commit()
        log.info("Instrução %s %s", instruction_id, label)
        return True

    def run_eod(self) -> dict:
        """Fecho do dia: liquida as instruções devidas, escreve o relatório e avança a data de negócio."""
        bd = self.business_date()
        log.info("Início do fecho do dia (EOD) de %s", bd.isoformat())
        settled, not_settled = [], []
        for ins in self.db.due_instructions(bd):
            if ins["status"] == "PENDING":
                self.db.update_instruction(ins["instruction_id"], "SETTLED", bd)
                ins["status"], ins["settled_on"] = "SETTLED", bd.isoformat()
                settled.append(ins)
                log.info("Instrução %s LIQUIDADA (%s)", ins["instruction_id"], bd.isoformat())
            else:
                not_settled.append(ins)
                log.warning("Instrução %s NÃO liquidada na data prevista: estado %s",
                            ins["instruction_id"], ins["status"])
        report = self._write_report(bd, settled + not_settled)
        next_bd = next_business_day(bd)
        self.db.set_state("business_date", next_bd.isoformat())
        self.db.commit()
        log.info("Fim do EOD de %s: %d liquidadas, %d por liquidar. Próxima data de negócio: %s",
                 bd.isoformat(), len(settled), len(not_settled), next_bd.isoformat())
        return {
            "business_date": bd.isoformat(),
            "settled": len(settled),
            "not_settled": len(not_settled),
            "report_file": report,
            "next_business_date": next_bd.isoformat(),
        }

    def _write_report(self, bd: date, rows) -> str:
        os.makedirs(EOD_DIR, exist_ok=True)
        path = os.path.join(EOD_DIR, f"settlement_{bd.strftime('%Y%m%d')}.csv")
        fields = ["instruction_id", "trade_id", "symbol", "qty", "amount", "trade_date",
                  "intended_settlement_date", "status", "settled_on"]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for r in rows:
                writer.writerow({k: (v.isoformat() if isinstance(v, date) else v) for k, v in r.items()})
        return path
