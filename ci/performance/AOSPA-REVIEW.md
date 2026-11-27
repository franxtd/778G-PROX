# Revisão de desempenho AOSPA / Dubai

Fonte oficial: AOSPA/android_kernel_motorola_sm7325, branch uvite,
snapshot c7b94bfc09cde1e8be7e32a65809f1b3bec98f3f.
O BoardConfig oficial do Dubai seleciona dubai-qgki_defconfig nessa árvore.
A análise foi feita contra a base FranBakaSU 5.4.286/WALT, sem substituir
os drivers, as tabelas de frequência ou a configuração inteira da ROM.

## Integrado

| Commit AOSPA | Mudança | Verificação e limite |
| --- | --- | --- |
| [27f83c59](https://github.com/AOSPA/android_kernel_motorola_sm7325/commit/27f83c591797b0accecc62bebbc6ba2ab70be76a) | Permite MADV_PAGEOUT das páginas anônimas COW de um mapeamento privado de arquivo, mesmo sem direito de escrita no arquivo original. Mantém a proteção das páginas de arquivo compartilhadas. | A base ainda tinha o teste antigo que rejeitava todo o VMA. Patch aplicado sem conflito. Teste QEMU usa o módulo zRAM real, um arquivo pertencente a root, filho UID 1000, pagemap e roundtrip de dados. Não há estimativa de ganho de RAM no telefone. |
| [cfb5aec2](https://github.com/AOSPA/android_kernel_motorola_sm7325/commit/cfb5aec2896d48f1e32c20c797344f61e6d3a858) | Remove o ring buffer privado de debug do LPM, sua alocação DMA e o spinlock executado em eventos frequentes de entrada/saída de idle. | Tracepoints e printk permanecem. Não altera a política de idle, os estados PSCI ou os limites térmicos. Compilação/ABI são verificadas; o idle do hardware Qualcomm precisa de teste físico. |

Esses patches conservam as assinaturas e os layouts das interfaces dos
módulos. A comparação dos CRCs é feita pelo build, sem fixar CRCs à mão.

## Analisado e mantido fora desta revisão

| Candidato | Decisão |
| --- | --- |
| b741a79c: worker de GPU de baixa prioridade | O snapshot acrescenta estruturas e uma segunda thread, mas signal_event ainda enfileira em device->events_worker sem selecionar event->prio. Exige completar o roteamento, auditar teardown e avaliar a ABI antes de atribuir benefício. |
| f87b61b1: prioridade RT do worker KGSL de 2 para 16 | Está associado ao redesenho das filas acima. Requer medir latência e concorrência com outras tarefas RT. |
| fd0f1e33: carga do Adreno em HFR | Multiplica busy_time por refresh_rate/60 depois do clamp existente; a divisão inteira e a relação busy/total precisam ser calibradas. Não foi tratado como correção universal para 90/120/144 Hz. |
| ba89d25f: atalho para GPU com apenas um OPP | Só traz benefício quando existe um único estado de frequência. Não justifica alterar a seleção do governador na configuração normal com múltiplos OPPs. |
| 0fe32129: prefetch em todas as operações LSE | É uma hipótese de microarquitetura. Precisa de comparação no 778G+; acrescentar hints em todos os atomics não comprova ganho em jogos. |
| b15a1496: desativar PROCESS_RECLAIM | Remove uma interface /proc usada por alguns componentes de ROM. Foi preservada nesta revisão; a correção de MADV_PAGEOUT atua no reclaim existente. |
| 00b31b0f: UCLAMP_BUCKETS_COUNT=20 | Fora do escopo, que pediu desfazer os ajustes extras de UClamp. Também muda estruturas internas relevantes à ABI. |
| 0552a580: desativar CFI | CFI foi preservado, inclusive no Full LTO. |
| a1aae6f3: trocar -O2 por -O3 | Mantido -O2 para não acumular mudanças de geração de código junto com Full LTO/AutoFDO antes de medir o resultado. |
| ff3e18c0: GPU speed bin / mudanças em DT | Tabelas de OPP, tensão e DTB da base funcional foram preservadas. |

## Full LTO e AutoFDO

O defconfig passa a selecionar Full LTO: CONFIG_LTO_CLANG=y e
CONFIG_THINLTO desativado. O workflow oferece Full e Thin para comparação,
testa o consumo de perfis nos dois modos com um programa sintético e usa
recursos de memória/swap apenas no runner de compilação. CFI permanece.

O build collect/PREPARE adiciona metadados de coleta de AutoFDO. Sem um perfil
real do aparelho, ele não é um build otimizado por AutoFDO. Full LTO também
não é uma promessa de FPS superior: esse resultado exige medição no telefone.

## FAS

A geração do ZIP do módulo fas-rs foi removida do workflow e o script
ci/fas/package-module.py foi excluído. O módulo já instalado no telefone
é independente dessa remoção. Os backports BPF e o teste de 400 uprobes
permanecem. Licenças e atribuições do código de terceiros são preservadas.

## Teste novo de reclaim

O teste cria zRAM de 4 MiB **somente dentro do QEMU**, habilita swap, testa
MADV_PAGEOUT de páginas privadas sem autorização de escrita no arquivo,
confere o bit de swap no pagemap e os dados após a leitura de volta. Testa
também que a página compartilhada não autorizada continua residente.
O teste desativa swap e descarrega zRAM ao terminar. Nenhuma dessas ações
é executada no aparelho pelo ZIP de instalação.
