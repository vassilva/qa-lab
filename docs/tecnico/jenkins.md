# Jenkins no QA Lab

Jenkins do laboratório em `localhost:8090` (admin / admin), definido **como código**:

| Ficheiro | O que define |
| --- | --- |
| `jenkins/Dockerfile` | Imagem: Jenkins LTS + cliente Docker + Python |
| `jenkins/plugins.txt` | Plugins (Pipeline, Git, JUnit, Configuration as Code, Job DSL, Timestamper) |
| `jenkins/casc.yaml` | Utilizador, segurança e o job `qa-lab-pipeline` (verifica o Git a cada 2 minutos) |
| `Jenkinsfile` | O pipeline, versionado com o código |

Apagar o Jenkins e voltar a criá-lo dá exatamente o mesmo resultado, sem cliques manuais.

## Pipeline

```
Preparar → Build da imagem → Testes de componente e API
  → QA · Deploy → QA · Smoke → QA · Regressão BDD
  → UAT · Deploy → UAT · Smoke → UAT · Resumo de testes → UAT · Go/No-go
```

| Conceito | Onde está no Jenkinsfile |
| --- | --- |
| Gate de qualidade | Qualquer falha em "QA · …" pára o pipeline: a versão não chega a UAT |
| Promoção de artefacto | A imagem `qa-lab:<versão>-<commit>` é construída uma vez e promovida |
| Parâmetros | `REGRESSAO` (completa/critica) e `MODO_DESAFIO` (defeitos escondidos em QA) |
| Disparos | Commit (pollSCM a cada 2 min), manual, e `cron('H 2 * * 1-5')`: regressão noturna em QA |
| Execução condicional | `when { not { triggeredBy 'TimerTrigger' } }`: a regressão noturna não passa para UAT |
| Aprovação manual | Estágio `input` "UAT · Go/No-go", com timeout de 1 dia |
| Relatórios | `junit` (separador Tests e tendência), `archiveArtifacts` (relatório HTML, cobertura) |
| Pós-ações | `post { always / success / failure }` |
| Sem execuções em paralelo | `disableConcurrentBuilds()`: dois deploys nunca se cruzam |

## Exercícios

1. **Build with Parameters** → `critica`: compara o tempo do estágio de regressão com a regressão completa.
2. **Build with Parameters** → `MODO_DESAFIO`: o pipeline deve parar em "QA · Regressão BDD". Abre o separador **Tests** e identifica os 8 cenários falhados.
3. Num build verde, descarrega o artefacto `reports/qa/index.html` e abre o relatório.
4. **Restart from Stage**: num build falhado por infraestrutura, repete só a partir do estágio que falhou.
5. **Replay**: altera o `echo` final no browser e corre, sem fazer commit. Para que serve isto e porque não substitui um commit?
6. Faz um commit com um cenário BDD que falha de propósito e observa: falha em QA, nada chega a UAT. Depois `git revert`.
7. Explica a diferença entre `pollSCM` e um webhook (o GitHub avisa o Jenkins) e porque é que aqui usamos polling.
