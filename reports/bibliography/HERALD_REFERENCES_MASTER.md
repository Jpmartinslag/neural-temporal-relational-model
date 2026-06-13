# HERALD — References Master List

**Created:** 2026-06-10  
**Method:** Extracted from all reports, LaTeX, and Markdown files in the repository; supplemented by web search for new references (Part F).  
**Verification policy:** Each reference is classified by verification status. Unverified references must not be cited as primary evidence.

**Status legend:**
- `VERIFIED_PRIMARY` — DOI resolved to official publisher page
- `VERIFIED_INSTITUTIONAL` — Official institutional source (Eurostat, INE, etc.)
- `PREPRINT` — arXiv/HAL/OpenReview, not yet peer-reviewed
- `UNVERIFIED` — Not yet checked against primary source
- `POSSIBLE_HALLUCINATION` — Cannot be confirmed; use with extreme caution
- `SUPERSEDED_VERSION` — Preprint exists with published version; note both

---

## Axis 1 — Economic Complexity and Product Space

### R-001 — Hidalgo, Klinger, Barabási, Hausmann (2007)
**Key:** `hidalgo2007productspace`  
**Title:** The Product Space Conditions the Development of Nations  
**Authors:** C.A. Hidalgo, B. Klinger, A.-L. Barabási, R. Hausmann  
**Year:** 2007  
**Venue:** *Science*, 317, 482–487  
**DOI:** https://doi.org/10.1126/science.1144581  
**Status:** `VERIFIED_PRIMARY`  
**Theme:** Product space, economic complexity, diversification  
**Used in project:** Background for product relatedness and territorial capability  
**Claim supported:** Countries diversify into products close in the product space  

### R-002 — Hidalgo & Hausmann (2009)
**Key:** `hidalgo2009buildingblocks`  
**Title:** The Building Blocks of Economic Complexity  
**Authors:** C.A. Hidalgo, R. Hausmann  
**Year:** 2009  
**Venue:** *Proceedings of the National Academy of Sciences* (PNAS), 106, 10570–10575  
**DOI:** https://doi.org/10.1073/pnas.0900943106  
**Status:** `VERIFIED_PRIMARY`  
**Theme:** Economic complexity, ECI, PCI  
**Used in project:** Economic complexity indices as territory characterization  
**Claim supported:** Economic complexity predicts growth; sophistication measurable from export basket  

---

## Axis 2 — Territorial Recommendation and Production Systems

### R-003 — Pachot, Albouy-Kissi A., Albouy-Kissi B., Chausse (2021)
**Key:** `pachot2021production2vec`  
**Title:** Production2Vec: A Hybrid Recommender System Combining Semantic and Product Complexity Approach to Improve Industrial Resiliency  
**Authors:** Arnault Pachot, Adélaïde Albouy-Kissi, Benjamin Albouy-Kissi, Frédéric Chausse  
**Year:** 2021  
**Venue:** *Proceedings of the 2021 2nd International Conference on Artificial Intelligence and Information Systems* (ICAIIS '21), ACM  
**DOI:** https://doi.org/10.1145/3469213.3469218  
**HAL:** https://hal.science/hal-03276942  
**Status:** `VERIFIED_PRIMARY` (ACM DL + HAL confirmed)  
**Theme:** Production recommender system, product complexity, Word2Vec, industrial resilience  
**Used in project:** Foundational work for the recommendation component (Bloco 3)  
**Claim supported:** Hybrid semantic + economic complexity approach for industrial recommendation  
**Note:** This project does not have access to the Atlas des Synergies Productives software or its private data  

### R-004 — Pachot, Albouy-Kissi A., Albouy-Kissi B., Chausse (2021b)
**Key:** `pachot2021multiobjective`  
**Title:** Multiobjective Recommendation for Sustainable Production Systems  
**Authors:** Arnault Pachot, Adélaïde Albouy-Kissi, Benjamin Albouy-Kissi, Frédéric Chausse  
**Year:** 2021  
**Venue:** *MORS@RecSys 2021* (Workshop on Multi-Objective Recommender Systems at RecSys)  
**GitHub:** https://github.com/apachot/Multiobjective-recommendation-for-sustainable-production-systems  
**Status:** `VERIFIED_INSTITUTIONAL` (GitHub code confirmed; workshop proceedings UNVERIFIED)  
**Theme:** Multi-objective recommendation, sustainable production, economic complexity  
**Used in project:** Framework for territorial recommendation objectives  
**Claim supported:** Recommendation can balance economic and sustainability objectives  

### R-005 — Pachot, Albouy-Kissi, Albouy-Kissi, Chausse (2022)
**Key:** `pachot2022decisionsupport`  
**Title:** Decision Support System for Distributed Manufacturing Based on Input-Output Analysis and Economic Complexity  
**Authors:** Arnault Pachot, Adélaïde Albouy-Kissi, Benjamin Albouy-Kissi, Frédéric Chausse  
**Year:** 2022  
**Venue:** *8th International Multidisciplinary Conference on Economics, Business Engineering and Social Sciences*  
**arXiv:** https://arxiv.org/abs/2201.00694  
**HAL:** https://hal.science/hal-03500970v1  
**Status:** `VERIFIED_PRIMARY` (arXiv + HAL confirmed)  
**Theme:** Decision support, input-output analysis, economic complexity, distributed manufacturing  
**Used in project:** Input-output approach for territorial production recommendation  
**Claim supported:** I-O analysis + product space can identify local substitution suppliers  

---

## Axis 3 — Dynamic and Temporal Graphs

### R-006 — Hallac, Park, Boyd, Leskovec (2017)
**Key:** `hallac2017tvgl`  
**Title:** Network Inference via the Time-Varying Graphical Lasso  
**Authors:** David Hallac, Youngsuk Park, Stephen Boyd, Jure Leskovec  
**Year:** 2017  
**Venue:** *KDD 2017*, ACM  
**DOI:** https://doi.org/10.1145/3097983.3098037  
**arXiv:** https://arxiv.org/abs/1703.01958  
**Status:** `VERIFIED_PRIMARY`  
**Theme:** Time-varying graph, sparse inverse covariance, temporal network inference  
**Used in project:** Candidate method for G2 (learned sparse graph)  
**Claim supported:** TVGL infers time-varying sparse networks from time series; handles structural change  
**Risk:** T≈13 is far below typical requirements; strong regularization needed  

### R-007 — Matias & Miele (2017)
**Key:** `matias2017dsbm`  
**Title:** Statistical Clustering of Temporal Networks Through a Dynamic Stochastic Block Model  
**Authors:** Catherine Matias, Vincent Miele  
**Year:** 2017  
**Venue:** *Journal of the Royal Statistical Society: Series B*, 79(4), 1119–1141  
**DOI:** https://doi.org/10.1111/rssb.12200  
**arXiv:** https://arxiv.org/abs/1506.07464  
**Status:** `VERIFIED_PRIMARY`  
**Theme:** Dynamic stochastic block model, temporal community detection, Markov chain node transitions  
**Used in project:** Candidate method for G2/G3 (dynamic community detection)  
**Risk:** Requires sufficient T and dense enough networks; validate for T≈13  

### R-008 — EconoGNN (2026)
**Key:** `econognn2026`  
**Title:** EconoGNN: A Graph Neural Network Framework for Temporal Economic Resilience Insights  
**Authors:** Marcus Araujo, Francisco Rodrigues, Elaine Sousa
**Year:** 2026  
**Venue:** *PLOS One*, 21(4), e0343683  
**DOI:** https://doi.org/10.1371/journal.pone.0343683  
**Status:** `VERIFIED_PRIMARY` (official PLOS ONE article checked 2026-06-11)
**Theme:** GNN, economic resilience, temporal, 183 countries, UN COMTRADE, Penn World Table  
**Used in project:** Methodological reference for observed dynamic economic graphs and GConvGRU
**Claim supported:** Temporal graph learning has been evaluated on an observed dynamic country-level trade network
**Risk:** Classification, national scale, richer temporal panel and different validation protocol; reference only, not a HERALD base implementation

---

## Axis 4 — Sparse Graph Learning and Graphical Models

### R-009 — Friedman, Hastie, Tibshirani (2008)
**Key:** `friedman2008glasso`  
**Title:** Sparse Inverse Covariance Estimation with the Graphical Lasso  
**Authors:** Jerome Friedman, Trevor Hastie, Robert Tibshirani  
**Year:** 2008  
**Venue:** *Biostatistics*, 9(3), 432–441  
**DOI:** https://doi.org/10.1093/biostatistics/kxm045  
**Status:** `VERIFIED_PRIMARY` (DOI confirmed: https://doi.org/10.1093/biostatistics/kxm045)  
**Theme:** Graphical Lasso, sparse precision matrix, regularization  
**Used in project:** Foundational method for G2  
**Claim supported:** L1-penalized inverse covariance estimation yields sparse graphs  

### R-010 — Shojaie & Fox (2022)
**Key:** `shojaie2022granger`  
**Title:** Granger Causality: A Review and Recent Advances  
**Authors:** Ali Shojaie, Emily B. Fox  
**Year:** 2022  
**Venue:** *Annual Review of Statistics and Its Application*, 9  
**arXiv:** https://arxiv.org/abs/2105.02675  
**Status:** `UNVERIFIED` (arXiv confirmed; journal DOI to be verified)  
**Theme:** Granger causality, limitations, VAR, neural extensions  
**Used in project:** Methodological caution: Granger ≠ structural causality  
**Claim supported:** Granger predictability is not economic causality; must be clearly labeled  

---

## Axis 5 — Regime Learner and Temporal Models (France context)

### R-011 — Hamilton (1989)
**Key:** `hamilton1989regime`  
**Title:** A New Approach to the Economic Analysis of Nonstationary Time Series and the Business Cycle  
**Authors:** J.D. Hamilton  
**Year:** 1989  
**Venue:** *Econometrica*, 57(2), 357–384  
**DOI:** https://doi.org/10.2307/1912559  
**Status:** `VERIFIED_PRIMARY`  
**Theme:** Markov regime switching, business cycle  
**Used in project:** Background for HERALD regime learner design  

### R-012 — Kim (1994)
**Key:** `kim1994dynamic`  
**Title:** Dynamic Linear Models with Markov-Switching  
**Authors:** C.-J. Kim  
**Year:** 1994  
**Venue:** *Journal of Econometrics*, 60(1–2), 1–22  
**DOI:** https://doi.org/10.1016/0304-4076(94)90036-1  
**Status:** `VERIFIED_PRIMARY`  
**Theme:** Switching state-space, Kalman filter + regime  
**Used in project:** Background for HERALD regime learner  

### R-013 — Truong, Oudre, Vayatis (2020)
**Key:** `truong2020ruptures`  
**Title:** Selective Review of Offline Change Point Detection Methods  
**Authors:** Charles Truong, Laurent Oudre, Nicolas Vayatis  
**Year:** 2020  
**Venue:** *Signal Processing*, 167, 107299  
**DOI:** https://doi.org/10.1016/j.sigpro.2019.107299  
**Status:** `VERIFIED_PRIMARY`  
**Theme:** Change-point detection, PELT, BOCPD, CUSUM  
**Used in project:** Candidate method for G3 (economic regime detection on graphs)  

### R-014 — Jacobs et al. (1991)
**Key:** `jacobs1991adaptive`  
**Title:** Adaptive Mixtures of Local Experts  
**Authors:** R.A. Jacobs, M.I. Jordan, S.J. Nowlan, G.E. Hinton  
**Year:** 1991  
**Venue:** *Neural Computation*, 3(1), 79–87  
**DOI:** https://doi.org/10.1162/neco.1991.3.1.79  
**Status:** `VERIFIED_PRIMARY`  
**Theme:** Mixture of experts, gating, local specialization  
**Used in project:** Background for HERALD regime architecture  

---

## Axis 6 — Regional Economics and Enterprise Birth

### R-015 — Eurostat Business Demography Methodology
**Key:** `eurostat_bd_methodology`  
**Title:** Business Demography Statistics — Methodology  
**Authors:** Eurostat  
**Year:** 2021 (last revision)  
**URL:** https://ec.europa.eu/eurostat/statistics-explained/index.php/Business_demography_statistics  
**Status:** `VERIFIED_INSTITUTIONAL`  
**Theme:** Enterprise birth definition, OECD/Eurostat demographic concept, two-year reactivation rule  
**Used in project:** Canonical definition for harmonized Path H target  

### R-016 — Audretsch & Fritsch (2002)
**Key:** `audretsch2002growth`  
**Title:** Growth Regimes over Time and Space  
**Authors:** David B. Audretsch, Michael Fritsch  
**Year:** 2002  
**Venue:** *Regional Studies*, 36(2), 113–124  
**DOI:** https://doi.org/10.1080/00343400220121909  
**Status:** `UNVERIFIED` (standard reference; DOI to be confirmed)  
**Theme:** New firm formation, regional growth, entrepreneurship  
**Used in project:** Background for enterprise birth as economic indicator  

---

## Axis 7 — Spatial Econometrics

### R-017 — Anselin (1988) — Spatial Econometrics
**Key:** `anselin1988spatial`  
**Title:** Spatial Econometrics: Methods and Models  
**Authors:** Luc Anselin  
**Year:** 1988  
**Venue:** Kluwer Academic Publishers  
**DOI:** https://doi.org/10.1007/978-94-015-7799-1  
**Status:** `UNVERIFIED` (standard textbook; DOI to be confirmed)  
**Theme:** Spatial autocorrelation, Moran's I, spatial lag, spatial error models  
**Used in project:** Theoretical basis for Phase 4O-C Moran's I protocol  

### R-018 — Moran (1950)
**Key:** `moran1950spatial`  
**Title:** Notes on Continuous Stochastic Phenomena  
**Authors:** P.A.P. Moran  
**Year:** 1950  
**Venue:** *Biometrika*, 37(1/2), 17–23  
**DOI:** https://doi.org/10.2307/2332142  
**Status:** `UNVERIFIED` (classic reference; DOI to be confirmed)  
**Theme:** Moran's I, spatial autocorrelation  
**Used in project:** Primary statistic in Phase 4O-C  

---

## Axis 8 — Explainability in Graph Models

### R-019 — Jain & Wallace (2019) — Attention not explanation
**Key:** `jain2019attention`  
**Title:** Attention Is Not Explanation  
**Authors:** Sarthak Jain, Byron C. Wallace  
**Year:** 2019  
**Venue:** *NAACL 2019*  
**arXiv:** https://arxiv.org/abs/1902.10186  
**Status:** `UNVERIFIED` (arXiv confirmed; proceedings DOI to be verified)  
**Theme:** Attention mechanism, explainability, faithfulness  
**Used in project:** Critical caution: attention weights ≠ economic explanation  
**Claim supported:** Attention weights are not reliable explanations; permutation test required  

---

---

## Axis 9 — Regional Diversification and Relatedness

### R-020 — Neffke, Henning & Boschma (2011)
**Key:** `neffke2011regions`  
**Title:** How Do Regions Diversify over Time? Industry Relatedness and the Development of New Growth Paths  
**Authors:** Frank Neffke, Martin Henning, Ron Boschma  
**Year:** 2011  
**Venue:** *Economic Geography*, 87(3), 237–265  
**Status:** `UNVERIFIED` (standard reference; DOI to be confirmed)  
**Theme:** Skill relatedness, regional diversification, labor flows, industry relatedness  
**Used in project:** Background for sector similarity edges (G1); relatedness concept  
**Risk:** Uses plant-level labor flow microdata not available at NUTS3 level for our project  

### R-021 — Acemoglu, Carvalho, Ozdaglar, Tahbaz-Salehi (2012)
**Key:** `acemoglu2012economy`  
**Title:** The Network Origins of Aggregate Fluctuations  
**Authors:** Daron Acemoglu, Vasco M. Carvalho, Asuman Ozdaglar, Alireza Tahbaz-Salehi  
**Year:** 2012  
**Venue:** *Econometrica*, 80(5), 1977–2016  
**DOI:** https://doi.org/10.3982/ECTA9623  
**Status:** `UNVERIFIED` (standard reference; DOI to be confirmed)  
**Theme:** Input-output networks, shock propagation, production networks  
**Used in project:** I-O edges in G1 (layer 5); Bloco 3 recommendation background  

### R-022 — Blondel, Guillaume, Lambiotte, Lefebvre (2008)
**Key:** `blondel2008louvain`  
**Title:** Fast Unfolding of Communities in Large Networks  
**Authors:** Vincent D. Blondel, Jean-Loup Guillaume, Renaud Lambiotte, Etienne Lefebvre  
**Year:** 2008  
**Venue:** *Journal of Statistical Mechanics: Theory and Experiment*, P10008  
**DOI:** https://doi.org/10.1088/1742-5468/2008/10/P10008  
**Status:** `UNVERIFIED` (standard reference; DOI to be confirmed)  
**Theme:** Community detection, Louvain algorithm, modularity  
**Used in project:** G2 static community detection baseline  

### R-023 — Adams & MacKay (2007)
**Key:** `adams2007bocpd`  
**Title:** Bayesian Online Changepoint Detection  
**Authors:** Ryan P. Adams, David J.C. MacKay  
**Year:** 2007  
**Venue:** *arXiv:0710.3742*  
**arXiv:** https://arxiv.org/abs/0710.3742  
**Status:** `PREPRINT` (widely cited; no published version found)  
**Theme:** BOCPD, online change-point detection, Bayesian  
**Used in project:** G3 change-point detection on edge weights  

### R-024 — Killick, Fearnhead & Eckley (2012)
**Key:** `killick2012pelt`  
**Title:** Optimal Detection of Changepoints with a Linear Computational Cost  
**Authors:** Rebecca Killick, Paul Fearnhead, Idris A. Eckley  
**Year:** 2012  
**Venue:** *Journal of the American Statistical Association*, 107(500), 1590–1598  
**DOI:** https://doi.org/10.1080/01621459.2012.737745  
**Status:** `VERIFIED_PRIMARY`  
**Theme:** PELT algorithm, efficient change-point detection  
**Used in project:** G3 change-point detection (cited in Phase 2 reports)  

### R-025 — Page (1954)
**Key:** `page1954cusum`  
**Title:** Continuous Inspection Schemes  
**Authors:** E.S. Page  
**Year:** 1954  
**Venue:** *Biometrika*, 41(1/2), 100–115  
**DOI:** https://doi.org/10.1093/biomet/41.1-2.100  
**Status:** `UNVERIFIED` (classic reference; DOI to be confirmed)  
**Theme:** CUSUM, sequential change detection  
**Used in project:** G3 change-point detection baseline  

---

## Axis 10 — Graph-based Time-Series Imputation (DEC-046)

### R-026 — Cini, Marisca & Alippi (2022) — GRIN
**Key:** `cini2022grin`
**Title:** Filling the G_ap_s: Multivariate Time Series Imputation by Graph Neural Networks
**Authors:** Andrea Cini, Ivan Marisca, Cesare Alippi
**Year:** 2022
**Venue:** *ICLR 2022*
**URL:** https://openreview.net/forum?id=kOu3-S3wJ7
**Code:** https://github.com/Graph-Machine-Learning-Group/grin
**Status:** `VERIFIED_PRIMARY`
**Theme:** Graph recurrent imputation, GCRNN, MCAR + block missing, spatiotemporal
**Used in project:** Reference architecture for graph-based imputation; REJECTED for direct use (T>>200 required)
**Claim supported:** GRIN achieves SOTA on traffic and air quality sensors; T>>200 datasets

### R-027 — Du, Cote & Liu (2023) — SAITS
**Key:** `du2023saits`
**Title:** SAITS: Self-Attention-based Imputation for Time Series
**Authors:** Wenjie Du, David Cote, Yan Liu
**Year:** 2023
**Venue:** *Expert Systems with Applications*
**URL:** https://arxiv.org/abs/2202.08516
**Code:** https://github.com/WenjieDu/SAITS
**Status:** `VERIFIED_PRIMARY`
**Theme:** Diagonal-masked self-attention, time series imputation without graph
**Used in project:** Reference for attention-based imputation head; no directed lag distinction

### R-028 — Tashiro, Song, Song & Ermon (2021) — CSDI
**Key:** `tashiro2021csdi`
**Title:** CSDI: Conditional Score-based Diffusion Models for Probabilistic Time Series Imputation
**Authors:** Yusuke Tashiro, Jiaming Song, Yang Song, Stefano Ermon
**Year:** 2021
**Venue:** *NeurIPS 2021*
**URL:** https://proceedings.neurips.cc/paper/2021/hash/cfe8504bda37b575c70ee1a8276f3486-Abstract.html
**Code:** https://github.com/ermongroup/CSDI
**Status:** `VERIFIED_PRIMARY`
**Theme:** Score-based diffusion, probabilistic imputation, temporal masking
**Used in project:** REJECTED (DEC-046): high compute, low interpretability, no directed graph

### R-029 — Liu et al. (2023) — PriSTI
**Key:** `liu2023pristi`
**Title:** PriSTI: A Conditional Diffusion Framework for Spatiotemporal Imputation
**Authors:** Mingzhe Liu et al.
**Year:** 2023
**Venue:** *ICDE 2023 / arXiv*
**URL:** https://arxiv.org/abs/2302.09746
**Status:** `PREPRINT`
**Theme:** Spatial-temporal diffusion imputation
**Used in project:** REJECTED (DEC-046): same limitations as CSDI; code not confirmed

### R-030 — You, Ma, Ding, Kochenderfer & Leskovec (2020) — GRAPE
**Key:** `you2020grape`
**Title:** Handling Missing Data with Graph Representation Learning
**Authors:** Jiaxuan You, Xiaobai Ma, Yi Ding, Mykel J. Kochenderfer, Jure Leskovec
**Year:** 2020
**Venue:** *NeurIPS 2020*
**URL:** https://proceedings.neurips.cc/paper/2020/hash/dc36f18a9a0a776671d4879cae69b551-Abstract.html
**Status:** `VERIFIED_PRIMARY`
**Theme:** Missing data as link prediction in bipartite graph
**Used in project:** Conceptual reference; no lag, no directed relations

---

## Axis 11 — Domain Adaptation and Test-Time Adaptation for Graphs (DEC-046)

### R-031 — Wu, Pan, Zhou, Chang & Zhu (2020) — UDAGCN
**Key:** `wu2020udagcn`
**Title:** Unsupervised Domain Adaptive Graph Convolutional Networks
**Authors:** Man Wu, Shirui Pan, Chuan Zhou, Xiaojun Chang, Xingquan Zhu
**Year:** 2020
**Venue:** *The Web Conference (WWW) 2020*
**URL:** https://dl.acm.org/doi/10.1145/3366423.3380219
**Code:** https://github.com/TrustAGI-Lab/UDAGCN
**Status:** `VERIFIED_PRIMARY`
**Theme:** Adversarial domain adaptation, node classification, GCN
**Used in project:** REJECTED (DEC-046): node classification, not temporal imputation

### R-032 — Jin, Zhao, Ding, Liu, Tang & Shah (2023) — GTrans
**Key:** `jin2023gtrans`
**Title:** Empowering Graph Representation Learning with Test-Time Graph Transformation
**Authors:** Wei Jin, Tong Zhao, Jiayuan Ding, Yozen Liu, Jiliang Tang, Neil Shah
**Year:** 2023
**Venue:** *ICLR 2023*
**URL:** https://openreview.net/forum?id=Lnxl5pr018
**Code:** https://github.com/ChandlerBang/GTrans
**Status:** `VERIFIED_PRIMARY`
**Theme:** Test-time graph transformation, topology shift adaptation
**Used in project:** REJECTED (DEC-046): resolves topology shift, not dynamics shift

---

## Axis 12 — Neural Relational Inference and Graph Structure Learning (DEC-046)

### R-033 — Kipf, Fetaya, Wang, Welling & Zemel (2018) — NRI
**Key:** `kipf2018nri`
**Title:** Neural Relational Inference for Interacting Systems
**Authors:** Thomas Kipf, Ethan Fetaya, Kuan-Chieh Wang, Max Welling, Richard Zemel
**Year:** 2018
**Venue:** *ICML 2018 (PMLR Vol. 80)*
**URL:** https://proceedings.mlr.press/v80/kipf18a/kipf18a.pdf
**Code:** https://github.com/ethanfetaya/NRI
**Status:** `VERIFIED_PRIMARY`
**Theme:** VAE graph structure learning, interacting systems, discrete latent graph
**Used in project:** FUTURE_ONLY (DEC-046): T>>50 and N>>20 required; T=20/N=9 insufficient

### R-034 — Shang, Chen & Bi (2021) — GTS
**Key:** `shang2021gts`
**Title:** Discrete Graph Structure Learning for Forecasting Multiple Time Series
**Authors:** Chao Shang, Jie Chen, Jinbo Bi
**Year:** 2021
**Venue:** *ICLR 2021*
**URL:** https://openreview.net/forum?id=WEHSlH5mOk
**Status:** `VERIFIED_PRIMARY`
**Theme:** Discrete graph learning, Gumbel-softmax, time series forecasting
**Used in project:** FUTURE_ONLY (DEC-046): designed for forecasting, not imputation; T>>50

### R-035 — Fatemi, El Asri & Kazemi (2021) — SLAPS
**Key:** `fatemi2021slaps`
**Title:** SLAPS: Self-Supervision Improves Structure Learning for Graph Neural Networks
**Authors:** Bahare Fatemi, Layla El Asri, Seyed Mehran Kazemi
**Year:** 2021
**Venue:** *NeurIPS 2021*
**URL:** https://proceedings.neurips.cc/paper/2021/file/bf499a12e998d178afd964adf64a60cb-Paper.pdf
**Status:** `VERIFIED_PRIMARY`
**Theme:** Self-supervision + graph structure learning, denoising autoencoder on features
**Used in project:** Reference for combining self-supervision with graph learning (PATH 2)

---

## Axis 13 — Self-Supervised and Masked Pretraining (DEC-046)

### R-036 — Hou, Liu, Cen, Dong, Yang, Wang & Tang (2022) — GraphMAE
**Key:** `hou2022graphmae`
**Title:** GraphMAE: Self-Supervised Masked Graph Autoencoders
**Authors:** Zhenyu Hou, Xiao Liu, Yukuo Cen, Yuxiao Dong, Hongxia Yang, Chunjie Wang, Jie Tang
**Year:** 2022
**Venue:** *KDD 2022*
**URL:** https://dl.acm.org/doi/abs/10.1145/3534678.3539321
**Code:** https://github.com/THUDM/GraphMAE
**Status:** `VERIFIED_PRIMARY`
**Theme:** Masked node feature reconstruction, graph pretraining, GNN encoder
**Used in project:** Conceptual basis for masked pretraining task in PATH 1 and PATH 2

### R-037 — Nie, Nguyen, Sinthong & Kalagnanam (2023) — PatchTST
**Key:** `nie2023patchtst`
**Title:** A Time Series is Worth 64 Words: Long-term Forecasting with Transformers
**Authors:** Yuqi Nie, Nam H. Nguyen, Phanwadee Sinthong, Jayant Kalagnanam
**Year:** 2023
**Venue:** *ICLR 2023*
**URL:** https://arxiv.org/abs/2211.14730
**Code:** https://github.com/yuqinie98/PatchTST
**Status:** `VERIFIED_PRIMARY`
**Theme:** Patch tokenization, masked time-series pretraining, long-horizon forecasting
**Used in project:** Reference for masked temporal pretraining; T=20 too short for full patches

### R-038 — Dong, Wu, Zhang, Zhang, Wang & Long (2023) — SimMTM
**Key:** `dong2023simmtm`
**Title:** SimMTM: A Simple Pre-Training Framework for Masked Time-Series Modeling
**Authors:** Jiaxiang Dong, Haixu Wu, Haoran Zhang, Li Zhang, Jianmin Wang, Mingsheng Long
**Year:** 2023
**Venue:** *NeurIPS 2023 (Spotlight)*
**URL:** https://proceedings.neurips.cc/paper_files/paper/2023/hash/5f9bfdfe3685e4ccdbc0e7fb29cccf2a-Abstract-Conference.html
**Code:** https://github.com/thuml/SimMTM
**Status:** `VERIFIED_PRIMARY`
**Theme:** Contrastive + masked reconstruction, time-series pretraining, temporal neighbors as positives
**Used in project:** Reference for contrastive pretraining objective; no graph component

---

## Axis 14 — Conformal Prediction for Temporal Data (DEC-046)

### R-039 — Xu & Xie (2021) — EnbPI
**Key:** `xu2021enbpi`
**Title:** Conformal Prediction Interval for Dynamic Time-Series
**Authors:** Chen Xu, Yao Xie
**Year:** 2021
**Venue:** *ICML 2021 (PMLR Vol. 139)*
**URL:** https://proceedings.mlr.press/v139/xu21h.html
**Code:** https://github.com/hamrel-cxu/EnbPI
**Status:** `VERIFIED_PRIMARY`
**Theme:** Conformal intervals, non-exchangeable time series, online calibration, distribution shift
**Used in project:** Recommended as uncertainty layer in PATH 1 (complementary)

### R-040 — Xu & Xie (2023) — SPCI
**Key:** `xu2023spci`
**Title:** Sequential Predictive Conformal Inference for Time Series
**Authors:** Chen Xu, Yao Xie
**Year:** 2023
**Venue:** *ICML 2023 (PMLR Vol. 202)*
**URL:** https://proceedings.mlr.press/v202/xu23r.html
**Code:** https://github.com/hamrel-cxu/SPCI-code
**Status:** `VERIFIED_PRIMARY`
**Theme:** Sequential conformal, quantile regression, conditional coverage
**Used in project:** Complementary uncertainty layer; T≥30 recommended for calibration

### R-041 — Barber, Candès, Ramdas & Tibshirani (2023)
**Key:** `barber2023conformal`
**Title:** Conformal Prediction Beyond Exchangeability
**Authors:** Rina Foygel Barber, Emmanuel J. Candès, Aaditya Ramdas, Ryan J. Tibshirani
**Year:** 2023
**Venue:** *Annals of Statistics*, 51(2), 816–845
**DOI:** https://doi.org/10.1214/23-AOS2276
**Status:** `VERIFIED_PRIMARY`
**Theme:** Conformal validity under covariate shift, weighted conformal prediction
**Used in project:** Theoretical basis for cross-country conformal coverage (distribution shift)

### R-042 — Angelopoulos & Bates (2023) — Tutorial
**Key:** `angelopoulos2023conformal`
**Title:** A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty Quantification
**Authors:** Anastasios N. Angelopoulos, Stephen Bates
**Year:** 2023 (arXiv v6)
**URL:** https://arxiv.org/abs/2107.07511
**Status:** `PREPRINT` (tutorial monograph, widely cited)
**Theme:** Conformal prediction tutorial, implementation guide
**Used in project:** Implementation reference for conformal layers

---

## Metrics

| Metric | Count |
|--------|------:|
| Total references | 42 |
| VERIFIED_PRIMARY | 28 |
| VERIFIED_INSTITUTIONAL | 2 |
| PREPRINT | 3 |
| UNVERIFIED | 9 |
| POSSIBLE_HALLUCINATION | 0 |
| Axes covered | 14 |

**Note on count:** The literature review comparative table (section 13) describes ~30 works, of which approximately 25 are explicitly keyed here. The remaining ~5 are referenced descriptively in the text (e.g. financial TVGL applications, product space Brazil analysis) without independent primary verification — they are not counted as references until verified.

**Priority verifications needed:**
1. R-010 (Shojaie 2022) — confirm Annual Review of Statistics DOI
2. R-016 (Audretsch 2002) — confirm Regional Studies DOI
3. R-017 (Anselin 1988) — confirm book DOI
4. R-018 (Moran 1950) — confirm Biometrika DOI
5. R-019 (Jain 2019) — confirm NAACL DOI
6. R-020 (Neffke 2011) — confirm Economic Geography DOI
7. R-021 (Acemoglu 2012) — confirm Econometrica DOI
8. R-022 (Blondel 2008) — confirm JSTAT DOI
9. R-025 (Page 1954) — confirm Biometrika DOI
