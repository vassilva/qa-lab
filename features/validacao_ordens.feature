# language: pt
Funcionalidade: Validação de ordens
  Como bolsa
  Quero rejeitar ordens inválidas antes de chegarem ao livro
  Para proteger o mercado de erros

  Contexto:
    Dado um mercado limpo com o preço de referência de "EDP" a 4.50 EUR

  @regression @boundary
  Esquema do Cenário: Limites de quantidade
    Quando é submetida uma ordem "C1" de compra de <quantidade> "EDP" a 4.50 EUR
    Então a ordem "C1" fica no estado "<estado>"

    Exemplos:
      | quantidade | estado   |
      | 0          | REJECTED |
      | 1          | NEW      |
      | 9999       | NEW      |
      | 10000      | NEW      |
      | 10001      | REJECTED |

  @regression
  Esquema do Cenário: Rejeição por preço
    Quando é submetida uma ordem "C1" de compra de 100 "EDP" a <preço> EUR
    Então a ordem "C1" é rejeitada com o motivo "<motivo>"

    Exemplos:
      | preço | motivo                  |
      | 4.505 | Preço fora do tick size |
      | 5.00  | Preço fora das bandas   |
      | 4.00  | Preço fora das bandas   |
      | 0     | Preço inválido          |

  @regression
  Cenário: Uma ordem já executada não pode ser cancelada
    Dado que existe uma ordem "V1" de venda de 100 "EDP" a 4.50 EUR
    E que existe uma ordem "C1" de compra de 100 "EDP" a 4.50 EUR
    Quando o participante tenta cancelar a ordem "V1"
    Então o cancelamento é recusado
