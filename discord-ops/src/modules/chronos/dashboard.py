@router.get("/dashboard", response_class=HTMLResponse)
async def chronos_dashboard():
    """Returns a rich, aesthetic HTML dashboard for Chronos."""
    try:
        exhumed = await ChronosService.exhume_keys()
        emap = await ChronosService.entropy_scan()
        usage = await ChronosService.cross_reference_usage(exhumed)
        ghosts = [k for k, v in usage.items() if v["status"] == "ghost"]
        
        # Build the HTML content with premium aesthetics
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Chronos Ghost Dashboard</title>
            <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;700&display=swap" rel="stylesheet">
            <style>
                :root {{
                    --bg: #0a0a0c;
                    --glass: rgba(255, 255, 255, 0.03);
                    --accent: #6d5dfc;
                    --hot: #ff4d4d;
                    --safe: #45b3e0;
                }}
                body {{
                    background: var(--bg);
                    color: #fff;
                    font-family: 'Outfit', sans-serif;
                    margin: 0;
                    padding: 40px;
                    overflow-x: hidden;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                }}
                .header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 60px;
                    animation: fadeInDown 0.8s ease;
                }}
                .header h1 {{
                    font-size: 3rem;
                    background: linear-gradient(135deg, #fff 0%, #666 100%);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    margin: 0;
                }}
                .stats-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 30px;
                    margin-bottom: 60px;
                }}
                .stat-card {{
                    background: var(--glass);
                    border: 1px solid rgba(255, 255, 255, 0.1);
                    backdrop-filter: blur(20px);
                    padding: 30px;
                    border-radius: 24px;
                    text-align: center;
                    transition: transform 0.3s ease;
                    animation: fadeInUp 1s ease;
                }}
                .stat-card:hover {{
                    transform: translateY(-10px);
                    border-color: var(--accent);
                }}
                .stat-val {{ font-size: 2.5rem; font-weight: 700; color: var(--accent); }}
                .stat-label {{ color: #888; text-transform: uppercase; letter-spacing: 2px; font-size: 0.8rem; margin-top: 10px; }}
                
                .entropy-list {{
                    margin-top: 60px;
                    animation: fadeIn 1.5s ease;
                }}
                .entropy-item {{
                    background: var(--glass);
                    margin-bottom: 10px;
                    padding: 20px;
                    border-radius: 12px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                .entropy-bar {{
                    height: 4px;
                    background: #222;
                    flex-grow: 1;
                    margin: 0 20px;
                    border-radius: 2px;
                    overflow: hidden;
                }}
                .entropy-fill {{ height: 100%; background: var(--accent); transition: width 1s ease; }}

                @keyframes fadeInDown {{ from {{ opacity: 0; transform: translateY(-20px); }} to {{ opacity: 1; transform: translateY(0); }} }}
                @keyframes fadeInUp {{ from {{ opacity: 0; transform: translateY(20px); }} to {{ opacity: 1; transform: translateY(0); }} }}
                @keyframes fadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Chronos Ghost Dashboard</h1>
                    <div class="status-badge" style="background: rgba(109, 93, 252, 0.2); color: var(--accent); padding: 8px 20px; border-radius: 100px; border: 1px solid var(--accent);">
                        SYSTEM: PREDATORY
                    </div>
                </div>

                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-val">{len(exhumed)}</div>
                        <div class="stat-label">Exhumed Targets</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-val">{len(ghosts)}</div>
                        <div class="stat-label">Active Ghosts</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-val">{round(emap['insights']['total_config_density'], 1)}</div>
                        <div class="stat-label">Flux Density</div>
                    </div>
                </div>

                <div class="entropy-list">
                    <h2 style="margin-bottom: 30px;">System Entropy Points</h2>
                    {"".join([f'''
                    <div class="entropy-item">
                        <span style="width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{path}</span>
                        <div class="entropy-bar"><div class="entropy-fill" style="width: {min(v['entropy']*10, 100)}%; background: {'var(--hot)' if v['entropy'] > 5 else 'var(--safe)'}"></div></div>
                        <span style="color: {'var(--hot)' if v['entropy'] > 5 else 'var(--safe)'}">{v['entropy']}e</span>
                    </div>
                    ''' for path, v in sorted(emap['map'].items(), key=lambda x: x[1]['entropy'], reverse=True)])}
                </div>
            </div>
        </body>
        </html>
        """
        return html
    except Exception as e:
        log.error(f"Dashboard failed: {e}")
        return HTMLResponse(content=f"Error: {e}", status_code=500)
