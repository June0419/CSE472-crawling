# Network Analysis Summary

## Information diffusion network

- Nodes: 931; directed edges: 461
- Density: 0.000532; average degree: 0.9903
- Weak components: 470; isolates: 375
- Largest weak component: 82 nodes (8.8%)
- Largest-component average path length: 16.8368; diameter: 45

The low density and the large number of isolates/components indicate that the collected discussion is fragmented rather than one continuous repost cascade. Because the edge is defined as parent/original post → reply/reblog, out-degree represents direct downstream responses in this sample.

### Highest-degree posts

1. @ai6yr@m.ai6yr.org — degree 7 (in 1, out 6)
2. @ai6yr@m.ai6yr.org — degree 6 (in 0, out 6)
3. @ai6yr@m.ai6yr.org — degree 5 (in 0, out 5)
4. @ai6yr@m.ai6yr.org — degree 4 (in 1, out 3)
5. @jeridansky@sfba.social — degree 4 (in 1, out 3)

## User interaction network

- Nodes: 200; undirected edges: 170
- Density: 0.008543; average degree: 1.7000
- Connected components: 65; isolates: 56
- Largest component: 125 nodes (62.5%)
- Average clustering coefficient: 0.1918
- Louvain communities: 78; modularity: 0.4417
- Largest-component average path length: 2.4894; diameter: 5

The user graph is still sparse, but its largest component contains a majority of sampled users. High modularity means interactions are organized into distinguishable clusters. Degree shows how many different sampled users an account interacted with; weighted degree also counts repeated interactions.

### Highest-degree users

1. @ai6yr@m.ai6yr.org — degree 91, weighted degree 405
2. @ikluft@avgeek.social — degree 18, weighted degree 91
3. @BakerRL75@m.ai6yr.org — degree 9, weighted degree 26
4. @jeridansky@sfba.social — degree 5, weighted degree 38
5. @exador23@m.ai6yr.org — degree 5, weighted degree 22

## Interpretation limits

These statistics describe the posts visible to `mastodon.social` under the selected hashtags and seed-user expansion. They are not estimates of all Mastodon activity or of the public as a whole. Path length and diameter are reported only for the largest component because the full graphs are disconnected. Centrality identifies structural prominence in this sample, not credibility or real-world influence.
