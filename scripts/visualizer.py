#!/usr/bin/env python3
"""
Visualization module for multi-project LOC analysis results
"""

import json
import os
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import argparse
from datetime import datetime

class LOCVisualizer:
    def __init__(self, results_file: str):
        """Initialize visualizer with analysis results"""
        with open(results_file, 'r') as f:
            self.results = json.load(f)
        self.output_dir = os.path.dirname(results_file)

    def create_all_visualizations(self):
        """Create all available visualizations"""
        print("Creating visualizations...")

        # Set style for matplotlib
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")

        self.create_language_distribution_chart()
        self.create_project_comparison_chart()
        self.create_change_analysis_chart()
        self.create_interactive_dashboard()

        print(f"Visualizations saved to {self.output_dir}")

    def create_language_distribution_chart(self):
        """Create language distribution pie chart"""
        language_data = self.results.get('language_percentages', {})
        if not language_data:
            return

        # Matplotlib version
        plt.figure(figsize=(12, 8))

        # Prepare data - group small languages into "Others"
        sorted_langs = sorted(language_data.items(), key=lambda x: x[1], reverse=True)
        main_langs = sorted_langs[:8]  # Top 8 languages
        other_langs = sorted_langs[8:]

        labels = [lang for lang, _ in main_langs]
        sizes = [pct for _, pct in main_langs]

        if other_langs:
            other_pct = sum(pct for _, pct in other_langs)
            labels.append('Others')
            sizes.append(other_pct)

        # Create pie chart
        colors = plt.cm.Set3(range(len(labels)))
        wedges, texts, autotexts = plt.pie(sizes, labels=labels, autopct='%1.1f%%',
                                          startangle=90, colors=colors)

        plt.title('Programming Language Distribution by Lines of Code', fontsize=16, fontweight='bold')
        plt.axis('equal')

        # Improve text readability
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')

        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'language_distribution.png'), dpi=300, bbox_inches='tight')
        plt.close()

        # Plotly interactive version
        fig = px.pie(values=sizes, names=labels, title='Programming Language Distribution')
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.write_html(os.path.join(self.output_dir, 'language_distribution_interactive.html'))

    def create_project_comparison_chart(self):
        """Create project comparison bar chart"""
        projects_data = []
        for project in self.results['projects']:
            info = project['info']
            loc = project['loc_stats']
            changes = project['change_stats']

            projects_data.append({
                'Project': info['name'][:20] + ('...' if len(info['name']) > 20 else ''),
                'Total LOC': loc['total_lines'],
                'Source LOC': loc['source_lines'],
                'Net Change': changes['net_change'],
                'Type': info['type']
            })

        df = pd.DataFrame(projects_data)

        if df.empty:
            return

        # Sort by Total LOC
        df = df.sort_values('Total LOC', ascending=True)

        # Create subplots
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

        # 1. Total LOC by project
        bars1 = ax1.barh(df['Project'], df['Total LOC'])
        ax1.set_xlabel('Lines of Code')
        ax1.set_title('Total Lines of Code by Project')
        ax1.ticklabel_format(style='plain', axis='x')

        # Add value labels on bars
        for i, bar in enumerate(bars1):
            width = bar.get_width()
            ax1.text(width + max(df['Total LOC']) * 0.01, bar.get_y() + bar.get_height()/2,
                    f'{int(width):,}', ha='left', va='center', fontsize=8)

        # 2. Source vs Total LOC
        x = range(len(df))
        width = 0.35
        ax2.bar([i - width/2 for i in x], df['Total LOC'], width, label='Total LOC', alpha=0.8)
        ax2.bar([i + width/2 for i in x], df['Source LOC'], width, label='Source LOC', alpha=0.8)
        ax2.set_xlabel('Projects')
        ax2.set_ylabel('Lines of Code')
        ax2.set_title('Source vs Total LOC Comparison')
        ax2.set_xticks(x)
        ax2.set_xticklabels(df['Project'], rotation=45, ha='right')
        ax2.legend()
        ax2.ticklabel_format(style='plain', axis='y')

        # 3. Net changes by project
        colors = ['green' if x >= 0 else 'red' for x in df['Net Change']]
        bars3 = ax3.barh(df['Project'], df['Net Change'], color=colors, alpha=0.7)
        ax3.set_xlabel('Net Change (Lines)')
        ax3.set_title('Net Code Changes by Project')
        ax3.axvline(x=0, color='black', linestyle='-', alpha=0.3)
        ax3.ticklabel_format(style='plain', axis='x')

        # 4. Project types distribution
        type_counts = df['Type'].value_counts()
        ax4.pie(type_counts.values, labels=type_counts.index, autopct='%1.1f%%')
        ax4.set_title('Project Types Distribution')

        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'project_comparison.png'), dpi=300, bbox_inches='tight')
        plt.close()

    def create_change_analysis_chart(self):
        """Create change analysis visualizations"""
        changes = self.results['changes']
        totals = self.results['totals']

        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

        # 1. Overall change summary
        change_data = {
            'Lines Added': changes['lines_added'],
            'Lines Removed': changes['lines_removed'],
            'Lines Modified': changes['lines_modified']
        }

        colors = ['green', 'red', 'orange']
        bars1 = ax1.bar(change_data.keys(), change_data.values(), color=colors, alpha=0.7)
        ax1.set_ylabel('Number of Lines')
        ax1.set_title('Overall Code Changes')
        ax1.ticklabel_format(style='plain', axis='y')

        # Add value labels
        for bar in bars1:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + max(change_data.values()) * 0.01,
                    f'{int(height):,}', ha='center', va='bottom')

        # 2. LOC composition
        loc_data = {
            'Source Code': totals['source_loc'],
            'Comments': totals['comment_loc'],
            'Blank Lines': totals['blank_loc']
        }

        ax2.pie(loc_data.values(), labels=loc_data.keys(), autopct='%1.1f%%',
                colors=['lightblue', 'lightgreen', 'lightgray'])
        ax2.set_title('Code Composition')

        # 3. Project activity (commits and contributors)
        project_activity = []
        for project in self.results['projects']:
            info = project['info']
            changes = project['change_stats']

            project_activity.append({
                'Project': info['name'][:15] + ('...' if len(info['name']) > 15 else ''),
                'Commits': changes['commits_count'],
                'Contributors': len(changes['contributors'])
            })

        activity_df = pd.DataFrame(project_activity)
        if not activity_df.empty:
            activity_df = activity_df.sort_values('Commits', ascending=True)

            x = range(len(activity_df))
            width = 0.35

            bars_commits = ax3.barh([i - width/2 for i in x], activity_df['Commits'],
                                  width, label='Commits', alpha=0.8)
            bars_contributors = ax3.barh([i + width/2 for i in x], activity_df['Contributors'],
                                       width, label='Contributors', alpha=0.8)

            ax3.set_yticks(x)
            ax3.set_yticklabels(activity_df['Project'])
            ax3.set_xlabel('Count')
            ax3.set_title('Project Activity (Commits vs Contributors)')
            ax3.legend()

        # 4. Change velocity
        total_projects = totals['projects_analyzed']
        if total_projects > 0:
            avg_changes_per_project = changes['net_change'] / total_projects
            avg_commits_per_project = changes['total_commits'] / total_projects

            velocity_data = {
                'Avg Net Change\nper Project': avg_changes_per_project,
                'Avg Commits\nper Project': avg_commits_per_project,
                'Total\nContributors': len(changes['all_contributors'])
            }

            bars4 = ax4.bar(velocity_data.keys(), velocity_data.values(),
                          color=['purple', 'brown', 'pink'], alpha=0.7)
            ax4.set_ylabel('Count')
            ax4.set_title('Development Velocity Metrics')

            # Add value labels
            for bar in bars4:
                height = bar.get_height()
                ax4.text(bar.get_x() + bar.get_width()/2., height + max(velocity_data.values()) * 0.01,
                        f'{height:.1f}' if height < 100 else f'{int(height):,}',
                        ha='center', va='bottom')

        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, 'change_analysis.png'), dpi=300, bbox_inches='tight')
        plt.close()

    def create_interactive_dashboard(self):
        """Create interactive Plotly dashboard"""
        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Language Distribution', 'Project LOC Comparison',
                          'Change Activity', 'Project Types'),
            specs=[[{"type": "pie"}, {"type": "bar"}],
                   [{"type": "bar"}, {"type": "pie"}]]
        )

        # 1. Language distribution (pie chart)
        language_data = self.results.get('language_percentages', {})
        if language_data:
            sorted_langs = sorted(language_data.items(), key=lambda x: x[1], reverse=True)
            main_langs = sorted_langs[:8]
            other_langs = sorted_langs[8:]

            labels = [lang for lang, _ in main_langs]
            values = [pct for _, pct in main_langs]

            if other_langs:
                other_pct = sum(pct for _, pct in other_langs)
                labels.append('Others')
                values.append(other_pct)

            fig.add_trace(
                go.Pie(labels=labels, values=values, name="Languages"),
                row=1, col=1
            )

        # 2. Project LOC comparison (bar chart)
        project_names = []
        project_locs = []
        for project in self.results['projects']:
            name = project['info']['name']
            loc = project['loc_stats']['total_lines']
            project_names.append(name[:20] + ('...' if len(name) > 20 else ''))
            project_locs.append(loc)

        fig.add_trace(
            go.Bar(x=project_names, y=project_locs, name="Total LOC"),
            row=1, col=2
        )

        # 3. Change activity (bar chart)
        project_changes = []
        for project in self.results['projects']:
            name = project['info']['name']
            net_change = project['change_stats']['net_change']
            project_changes.append(net_change)

        colors = ['green' if x >= 0 else 'red' for x in project_changes]
        fig.add_trace(
            go.Bar(x=project_names, y=project_changes, name="Net Change",
                   marker_color=colors),
            row=2, col=1
        )

        # 4. Project types (pie chart)
        type_counts = {}
        for project in self.results['projects']:
            ptype = project['info']['type']
            type_counts[ptype] = type_counts.get(ptype, 0) + 1

        fig.add_trace(
            go.Pie(labels=list(type_counts.keys()), values=list(type_counts.values()),
                   name="Project Types"),
            row=2, col=2
        )

        # Update layout
        fig.update_layout(
            title_text="Multi-Project LOC Analysis Dashboard",
            showlegend=False,
            height=800
        )

        # Save interactive dashboard
        fig.write_html(os.path.join(self.output_dir, 'interactive_dashboard.html'))


def main():
    parser = argparse.ArgumentParser(description='Create visualizations for LOC analysis results')
    parser.add_argument('--results', required=True, help='Path to analysis results JSON file')
    args = parser.parse_args()

    if not os.path.exists(args.results):
        print(f"Error: Results file {args.results} not found")
        return

    visualizer = LOCVisualizer(args.results)
    visualizer.create_all_visualizations()
    print("Visualizations created successfully!")


if __name__ == '__main__':
    main()