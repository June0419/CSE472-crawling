# User Network Measures

## Measures selected

1. **PageRank** estimates structural influence while considering the importance of connected accounts.
2. **Degree / 1-hop relations** counts each user's immediate distinct interaction partners.
3. **Betweenness centrality** identifies users that lie on shortest paths and may bridge groups.

## Local and global connectivity

- Local level: `user_node_measures.csv` reports `one_hop_relations` for every one of the 200 users.
- Global level: the average number of immediate relations is **1.70**.
- Isolates: **56 users** have zero relations in the collected graph.

The degree distribution is strongly right-skewed: most users have few immediate relations, while a small number of hubs connect to many accounts. This explains why the mean exceeds the typical user's degree.

## Highest degree

1. @ai6yr@m.ai6yr.org: 91
2. @ikluft@avgeek.social: 18
3. @BakerRL75@m.ai6yr.org: 9
4. @exador23@m.ai6yr.org: 5
5. @jeridansky@sfba.social: 5

## Highest PageRank

1. @ai6yr@m.ai6yr.org: 0.235818
2. @ikluft@avgeek.social: 0.051411
3. @MsMerope@sfba.social: 0.033117
4. @BakerRL75@m.ai6yr.org: 0.019431
5. @jeridansky@sfba.social: 0.018079

## Highest betweenness

1. @ai6yr@m.ai6yr.org: 0.373619
2. @ikluft@avgeek.social: 0.093498
3. @BakerRL75@m.ai6yr.org: 0.027723
4. @MiBaWi@m.ai6yr.org: 0.018578
5. @kevinrns@mstdn.social: 0.018425

## Interpretation

The PageRank histogram is concentrated at low values with a long upper tail, indicating that structural influence is concentrated in a small set of accounts. Betweenness is even more zero-inflated: many sampled users do not bridge shortest paths, while a few accounts connect otherwise separated parts of the largest interaction component. These measures describe prominence inside the collected sample, not trustworthiness or population-wide influence.
