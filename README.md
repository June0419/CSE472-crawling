# CSE 472 - Social Media Data Analysis

This project collects Mastodon disaster data and performs network analysis, Gephi visualization, and LLM-assisted content analysis.

## Implemented Features

- Verify that the Mastodon API token works.
- Collect deduplicated posts from multiple disaster hashtags, including reply context needed for network construction.
- Expand from seed users through mentions and replies in disaster-related posts, then fill remaining slots with authors of verified event posts.
- Store the final datasets in `data/posts.json` and `data/users.json`.

## 1. Prepare the Python Environment

Open PowerShell in the project directory and run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## 2. Configure Mastodon

Create a `.env` file in the project root with the following values:

```text
MASTODON_BASE_URL=https://your-mastodon-server
MASTODON_ACCESS_TOKEN=your-access-token
DISASTER_NAME=your-disaster-event-name
DISASTER_HASHTAGS=related_tag_1,related_tag_2,related_tag_3
SEED_USERS=user1@server.example,user2@server.example
```

The hashtag values do not need a leading `#`. Separate multiple values with commas. The `.env` file contains the real access token and must not be uploaded to GitHub. A safe configuration template is provided in `.env.example`.

## 3. Test the API Connection

```powershell
python src/test_connection.py
```

If the connection succeeds, the script prints the authenticated Mastodon account name.

## 4. Collect Data

Collect post data:

```powershell
python src/collect_posts.py
```

Collect user and interaction data:

```powershell
python src/collect_users.py
```

## 5. Build Networks and Gephi Files

```powershell
python src/build_networks.py
python src/plot_network_previews.py
```

The scripts create GEXF, GraphML, node CSV, and edge CSV files for both networks in `output/networks/`. Open the GEXF files in Gephi.

- `information_diffusion.gexf`: Posts are nodes, and directed edges point from original or parent posts to replies or reblogs.
- `user_network.gexf`: Users are nodes, and undirected edges represent mention, reply, or reblog interactions.

The PNG files in `output/figures/` are quick previews for checking the data and layouts. The final report uses images exported from Gephi with distinct layouts and degree-based node sizing.

## 6. Generate Final Visualizations with Gephi Toolkit

`GephiRender.java` uses the same engine as Gephi Desktop. It applies ForceAtlas2 to the information-diffusion network and Yifan Hu to the user network. Node size represents degree. Information-diffusion nodes are colored by post type, while user-network nodes are colored by modularity community.

```powershell
javac --release 17 -cp tools/gephi-toolkit-0.11.3-all.jar -d build/gephi src/GephiRender.java

& "tools/Gephi-0.11.3/jre-x64/jdk-17.0.20.1+1-jre/bin/java.exe" `
  --add-opens=java.base/java.net=ALL-UNNAMED `
  -cp "tools/gephi-toolkit-0.11.3-all.jar;build/gephi" `
  GephiRender information output/networks/information_diffusion.gexf output/gephi

& "tools/Gephi-0.11.3/jre-x64/jdk-17.0.20.1+1-jre/bin/java.exe" `
  --add-opens=java.base/java.net=ALL-UNNAMED `
  -cp "tools/gephi-toolkit-0.11.3-all.jar;build/gephi" `
  GephiRender users output/networks/user_network.gexf output/gephi
```

The `output/gephi/` directory contains a PNG, styled GEXF, and editable `.gephi` project for each network. The GEXF and Gephi project files preserve every node. Only zero-degree isolates are hidden in the report PNGs to improve readability.

## 7. Analyze Network Measures and LLM Keywords

```powershell
python src/analyze_networks.py
python src/plot_user_measures.py
ollama pull llama3.2:3b
python src/extract_keywords_llm.py
python src/analyze_content.py
```

The `output/analysis/` directory contains network metrics, 1-hop relations and centrality values for all 200 users, exactly three LLM-generated keywords per post, keyword frequencies, and written analyses. The `output/figures/` directory contains PageRank, degree, and betweenness distributions, along with the final word cloud and keyword-frequency chart.

- Because the networks are disconnected, path length and diameter are calculated only for the largest connected component.
- Keyword analysis uses the 500 posts collected directly from hashtag timelines. Context-only replies are excluded from keyword frequency calculations.
- Llama 3.2 3B runs locally through Ollama and generates exactly three keywords per post. No paid LLM API or additional API token is required.
- `extract_keywords_llm.py` saves intermediate results after every batch and resumes by default. Use `--overwrite` to restart from the beginning.

## 8. Generate the Final Report and Submission ZIP

After completing keyword extraction and analysis, run:

```powershell
python src/generate_report.py
python src/build_submission.py
```

- Final report: `output/pdf/CSE472_Project1_Report.pdf`
- Gradescope submission: `output/submission/CSE472_Project1_Submission.zip`

The submission ZIP excludes the real `.env` file, API tokens, local programs, temporary files, and the Java visualization helper. It contains the two required JSON datasets, Python source files, Gephi projects and images, analysis results, and the final PDF report.

Mastodon is decentralized, so the selected server returns only posts known to that instance. If the target count cannot be reached, add relevant hashtags or seed users, or use an instance with broader knowledge of the event.

## Official API Documentation

- [Mastodon API Introduction](https://docs.joinmastodon.org/client/intro/)
- [Hashtag Timelines](https://docs.joinmastodon.org/methods/timelines/#tag)
- [Accounts API](https://docs.joinmastodon.org/methods/accounts/)
