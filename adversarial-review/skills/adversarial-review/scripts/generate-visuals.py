#!/usr/bin/env python3
"""Generate review visualization charts from adversarial-review data.

Usage:
    generate-visuals.py --output <dir> --data <json_file>
    generate-visuals.py --output <dir> --inline <json_string>

The data JSON should have this structure:
{
    "topic": "review-topic",
    "date": "2026-04-08",
    "budget": {
        "limit": 200000,
        "consumed": 87500,
        "phases": {"phase1": 60000, "phase2": 15000, "phase3": 5000, "phase4": 7500},
        "agents": {"SEC": 35000, "CORR": 32000, "ARCH": 20500}
    },
    "funnel": {
        "raw": 24,
        "post_self_refinement": 12,
        "post_challenge": 8,
        "validated": 4,
        "dismissed": 4
    },
    "severity": {
        "Critical": 0,
        "Important": 0,
        "Minor": 3,
        "Trivial": 1
    },
    "convergence": {
        "SEC": [12, 5, 5],
        "CORR": [9, 7, 7]
    },
    "iterations": 2,
    "specialists": ["SEC", "CORR"]
}

Generates: budget.png, funnel.png, severity.png, convergence.png, summary.png (all-in-one)
"""

import argparse
import json
import sys
import os

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import numpy as np


# Color palette (dark theme, accessible)
COLORS = {
    'bg': '#1a1a2e',
    'fg': '#e0e0e0',
    'grid': '#2a2a4a',
    'accent1': '#e94560',   # red/coral
    'accent2': '#0f3460',   # deep blue
    'accent3': '#16213e',   # darker blue
    'accent4': '#533483',   # purple
    'accent5': '#e94560',   # coral
    'bar_consumed': '#e94560',
    'bar_remaining': '#2a2a4a',
    'critical': '#ff4444',
    'important': '#ff8c00',
    'minor': '#ffd700',
    'trivial': '#87ceeb',
    'agent_colors': ['#e94560', '#0f3460', '#533483', '#2ecc71', '#f39c12', '#9b59b6'],
    'funnel': ['#e94560', '#f39c12', '#2ecc71', '#87ceeb', '#666666'],
}


def setup_style():
    plt.rcParams.update({
        'figure.facecolor': COLORS['bg'],
        'axes.facecolor': COLORS['bg'],
        'axes.edgecolor': COLORS['grid'],
        'axes.labelcolor': COLORS['fg'],
        'text.color': COLORS['fg'],
        'xtick.color': COLORS['fg'],
        'ytick.color': COLORS['fg'],
        'grid.color': COLORS['grid'],
        'grid.alpha': 0.3,
        'font.family': 'monospace',
        'font.size': 11,
        'axes.titlesize': 14,
        'axes.titleweight': 'bold',
    })


def plot_budget(ax, data):
    """Token budget consumption gauge + phase breakdown."""
    budget = data['budget']
    limit = budget['limit']
    consumed = budget['consumed']
    remaining = limit - consumed
    pct = (consumed / limit) * 100 if limit > 0 else 0

    # Horizontal bar gauge
    ax.barh(['Budget'], [consumed], color=COLORS['bar_consumed'], height=0.4, label='Consumed')
    ax.barh(['Budget'], [remaining], left=[consumed], color=COLORS['bar_remaining'], height=0.4, label='Remaining')

    # Percentage label
    ax.text(consumed / 2, 0, f'{consumed:,} tokens ({pct:.0f}%)',
            ha='center', va='center', fontsize=10, fontweight='bold', color='white')
    ax.text(consumed + remaining / 2, 0, f'{remaining:,} remaining',
            ha='center', va='center', fontsize=9, color=COLORS['fg'], alpha=0.6)

    # Phase breakdown below
    phases = budget.get('phases', {})
    if phases:
        phase_names = list(phases.keys())
        phase_values = list(phases.values())
        colors = [COLORS['accent1'], COLORS['accent2'], COLORS['accent4'], '#2ecc71'][:len(phase_names)]

        y_offset = -0.8
        cumulative = 0
        for i, (name, val) in enumerate(zip(phase_names, phase_values)):
            ax.barh([y_offset], [val], left=[cumulative],
                    color=colors[i % len(colors)], height=0.3, alpha=0.8)
            if val > limit * 0.05:  # only label if wide enough
                ax.text(cumulative + val / 2, y_offset, f'{name}\n{val:,}',
                        ha='center', va='center', fontsize=7, color='white')
            cumulative += val

    ax.set_xlim(0, limit)
    ax.set_title('Token Budget', pad=15)
    ax.set_yticks([0])
    ax.set_yticklabels([''])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)

    # Agent breakdown as text
    agents = budget.get('agents', {})
    if agents:
        agent_text = '  '.join([f'{k}: {v:,}' for k, v in sorted(agents.items(), key=lambda x: -x[1])])
        ax.text(0.5, -0.15, f'Per agent: {agent_text}',
                transform=ax.transAxes, ha='center', fontsize=8, alpha=0.7)


def plot_funnel(ax, data):
    """Finding funnel: raw -> self-refinement -> challenge -> validated."""
    funnel = data['funnel']
    stages = ['Raw', 'Self-refined', 'Challenged', 'Validated']
    values = [
        funnel['raw'],
        funnel['post_self_refinement'],
        funnel['post_challenge'],
        funnel['validated']
    ]
    dismissed = funnel.get('dismissed', 0)

    # Horizontal funnel bars
    max_val = max(values) if values else 1
    colors = COLORS['funnel'][:len(stages)]

    bars = ax.barh(range(len(stages) - 1, -1, -1), values, color=colors, height=0.6, alpha=0.85)

    for i, (stage, val) in enumerate(zip(stages, values)):
        y = len(stages) - 1 - i
        ax.text(val + max_val * 0.02, y, f'{val}', va='center', fontsize=11, fontweight='bold')
        if i > 0 and values[i - 1] > 0:
            reduction = values[i - 1] - val
            if reduction > 0:
                pct = (reduction / values[i - 1]) * 100
                ax.text(val + max_val * 0.08, y - 0.15,
                        f'-{reduction} ({pct:.0f}%)', va='center', fontsize=8, alpha=0.5)

    ax.set_yticks(range(len(stages)))
    ax.set_yticklabels(list(reversed(stages)))
    ax.set_xlim(0, max_val * 1.3)
    ax.set_title('Finding Funnel', pad=15)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    if dismissed > 0:
        ax.text(0.95, 0.05, f'{dismissed} dismissed',
                transform=ax.transAxes, ha='right', fontsize=9, alpha=0.5,
                style='italic')


def plot_severity(ax, data):
    """Severity distribution donut chart."""
    severity = data['severity']
    labels = []
    sizes = []
    colors = []
    color_map = {
        'Critical': COLORS['critical'],
        'Important': COLORS['important'],
        'Minor': COLORS['minor'],
        'Trivial': COLORS['trivial'],
    }

    for level in ['Critical', 'Important', 'Minor', 'Trivial']:
        count = severity.get(level, 0)
        if count > 0:
            labels.append(f'{level} ({count})')
            sizes.append(count)
            colors.append(color_map[level])

    if not sizes:
        ax.text(0.5, 0.5, 'No findings', ha='center', va='center',
                transform=ax.transAxes, fontsize=14, alpha=0.5)
        ax.set_title('Severity Distribution', pad=15)
        return

    wedges, texts = ax.pie(sizes, labels=None, colors=colors,
                           startangle=90, wedgeprops={'width': 0.4, 'edgecolor': COLORS['bg']})

    total = sum(sizes)
    ax.text(0, 0, f'{total}', ha='center', va='center', fontsize=28, fontweight='bold')
    ax.text(0, -0.15, 'findings', ha='center', va='center', fontsize=10, alpha=0.6)

    ax.legend(labels, loc='lower center', ncol=2, fontsize=8,
              frameon=False, bbox_to_anchor=(0.5, -0.1))
    ax.set_title('Severity Distribution', pad=15)


def plot_convergence(ax, data):
    """Convergence curves: findings per iteration per agent."""
    convergence = data.get('convergence', {})
    if not convergence:
        ax.text(0.5, 0.5, 'No convergence data', ha='center', va='center',
                transform=ax.transAxes, fontsize=14, alpha=0.5)
        ax.set_title('Convergence', pad=15)
        return

    agent_colors = COLORS['agent_colors']
    max_iters = max(len(v) for v in convergence.values())
    if max_iters == 0:
        ax.text(0.5, 0.5, 'No convergence data', ha='center', va='center',
                transform=ax.transAxes, fontsize=14, alpha=0.5)
        ax.set_title('Agent Convergence', pad=15)
        return
    x = list(range(1, max_iters + 1))

    for i, (agent, findings) in enumerate(sorted(convergence.items())):
        color = agent_colors[i % len(agent_colors)]
        ax.plot(x[:len(findings)], findings, 'o-', color=color, linewidth=2,
                markersize=8, label=agent, markeredgecolor='white', markeredgewidth=1)

        # Annotate final value
        ax.annotate(f'{findings[-1]}', (len(findings), findings[-1]),
                    textcoords="offset points", xytext=(10, 0),
                    fontsize=9, color=color, fontweight='bold')

    ax.set_xlabel('Iteration')
    ax.set_ylabel('Findings')
    ax.set_title('Agent Convergence', pad=15)
    ax.set_xticks(x)
    ax.legend(frameon=False, fontsize=9)
    ax.grid(True, alpha=0.2)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # Mark convergence point
    for agent, findings in convergence.items():
        for j in range(1, len(findings)):
            if findings[j] == findings[j - 1]:
                ax.axvline(x=j + 1, color=COLORS['grid'], linestyle='--', alpha=0.3)
                break


def generate_summary(data, output_dir):
    """Generate all-in-one summary dashboard."""
    setup_style()
    fig = plt.figure(figsize=(16, 10))
    fig.suptitle(f'Adversarial Review: {data["topic"]}',
                 fontsize=18, fontweight='bold', y=0.98)
    fig.text(0.5, 0.95, f'{data["date"]} | {", ".join(data["specialists"])} | '
             f'{data["iterations"]} iterations',
             ha='center', fontsize=10, alpha=0.6)

    gs = GridSpec(2, 2, figure=fig, hspace=0.4, wspace=0.3,
                  left=0.08, right=0.95, top=0.9, bottom=0.08)

    ax1 = fig.add_subplot(gs[0, 0])
    plot_budget(ax1, data)

    ax2 = fig.add_subplot(gs[0, 1])
    plot_funnel(ax2, data)

    ax3 = fig.add_subplot(gs[1, 0])
    plot_severity(ax3, data)

    ax4 = fig.add_subplot(gs[1, 1])
    plot_convergence(ax4, data)

    path = os.path.join(output_dir, 'summary.png')
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return path


def generate_individual(data, output_dir):
    """Generate individual chart PNGs."""
    setup_style()
    paths = []

    for name, plot_fn in [('budget', plot_budget), ('funnel', plot_funnel),
                           ('severity', plot_severity), ('convergence', plot_convergence)]:
        fig, ax = plt.subplots(figsize=(8, 5))
        plot_fn(ax, data)
        path = os.path.join(output_dir, f'{name}.png')
        fig.savefig(path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        paths.append(path)

    return paths


def main():
    parser = argparse.ArgumentParser(description='Generate adversarial-review visualizations')
    parser.add_argument('--output', required=True, help='Output directory for charts')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--data', help='Path to JSON data file')
    group.add_argument('--inline', help='Inline JSON string')
    parser.add_argument('--individual', action='store_true',
                       help='Also generate individual chart files')
    args = parser.parse_args()

    if args.data:
        with open(args.data) as f:
            data = json.load(f)
    else:
        data = json.loads(args.inline)

    os.makedirs(args.output, exist_ok=True)

    summary_path = generate_summary(data, args.output)
    result = {'summary': summary_path}

    if args.individual:
        individual_paths = generate_individual(data, args.output)
        result['individual'] = individual_paths

    print(json.dumps(result))


if __name__ == '__main__':
    main()
