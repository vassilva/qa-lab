# language: pt
Funcionalidade: Execução de ordens limitadas
  Como participante de mercado
  Quero que as minhas ordens sejam cruzadas pela regra preço-tempo
  Para ter execuções justas e previsíveis

  Contexto:
    Dado um mercado limpo com o preço de referência de "EDP" a 4.50 EUR

  @smoke @regression
  Cenário: Compra que cruza com a melhor venda executa ao preço do livro
    Dado que existe uma ordem "V1" de venda de 100 "EDP" a 4.50 EUR
    Quando é submetida uma ordem "C1" de compra de 100 "EDP" a 4.55 EUR
    Então a ordem "C1" fica no estado "FILLED"
    E existe 1 negócio de 100 ações a 4.50 EUR
    E o livro de vendas de "EDP" fica vazio

  @regression
  Cenário: Execução parcial deixa o restante no livro
    Dado que existe uma ordem "V1" de venda de 100 "EDP" a 4.50 EUR
    Quando é submetida uma ordem "C1" de compra de 40 "EDP" a 4.50 EUR
    Então a ordem "C1" fica no estado "FILLED"
    E a ordem "V1" fica no estado "PARTIALLY_FILLED" com 60 por executar

  @regression
  Cenário: Com o mesmo preço, executa primeiro quem chegou antes
    Dado que existe uma ordem "C1" de compra de 100 "EDP" a 4.48 EUR
    E que existe uma ordem "C2" de compra de 100 "EDP" a 4.48 EUR
    Quando é submetida uma ordem "V1" de venda de 100 "EDP" a 4.48 EUR
    Então a ordem "C1" fica no estado "FILLED"
    E a ordem "C2" fica no estado "NEW"

  @regression
  Cenário: Ordem que não cruza fica no livro
    Dado que existe uma ordem "V1" de venda de 100 "EDP" a 4.52 EUR
    Quando é submetida uma ordem "C1" de compra de 100 "EDP" a 4.50 EUR
    Então a ordem "C1" fica no estado "NEW"
    E não existe nenhum negócio

  @regression
  Cenário: Ordem de mercado sem contraparte é cancelada
    Quando é submetida uma ordem "C1" de compra de 100 "EDP" a mercado
    Então a ordem "C1" fica no estado "CANCELLED"
