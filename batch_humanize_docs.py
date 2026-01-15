#!/usr/bin/env python3
"""
Batch Documentation Humanizer
Processes all user-facing documentation to remove AI writing indicators.

Author: Luke Steuber
"""

import sys
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple
from collections import defaultdict
import json

sys.path.insert(0, '/home/coolhand/shared')
from doc_humanizer import DocumentHumanizer

class BatchDocumentProcessor:
    """Batch processes documentation files with git integration."""

    def __init__(self, confidence_threshold: float = 0.8):
        self.humanizer = DocumentHumanizer()
        self.confidence_threshold = confidence_threshold
        self.stats = {
            'total_files': 0,
            'processed_files': 0,
            'skipped_files': 0,
            'error_files': 0,
            'total_indicators': 0,
            'indicators_by_type': defaultdict(int),
            'files_by_batch': {},
            'sample_transformations': []
        }
        self.start_time = datetime.now()

    def discover_files(self) -> Tuple[List[Path], List[Path], List[Path]]:
        """
        Discover all target files organized into batches.

        Returns:
            Tuple of (batch1_assessments, batch2_readmes, batch3_html_docs)
        """
        print("Discovering files...")

        # Batch 1: Assessment reports
        batch1 = []
        assessments_dir = Path('/home/coolhand/documentation/archive/assessments')
        if assessments_dir.exists():
            batch1 = list(assessments_dir.rglob('*.md'))

        # Batch 2: Project and server READMEs
        batch2 = []
        for base_dir in ['/home/coolhand/projects', '/home/coolhand/servers']:
            base_path = Path(base_dir)
            if base_path.exists():
                readmes = [p for p in base_path.rglob('README.md')
                          if 'CLAUDE.md' not in str(p)]
                batch2.extend(readmes)

        # Batch 3: HTML index files and public docs
        batch3 = []

        # HTML files (exclude node_modules)
        html_dir = Path('/home/coolhand/html')
        if html_dir.exists():
            html_files = [p for p in html_dir.rglob('index.html')
                         if 'node_modules' not in str(p)]
            batch3.extend(html_files)

        # Public documentation (exclude CLAUDE.md)
        docs_dir = Path('/home/coolhand/documentation')
        if docs_dir.exists():
            doc_files = [p for p in docs_dir.glob('*.md')
                        if 'CLAUDE' not in p.name]
            batch3.extend(doc_files)

        print(f"  Batch 1 (Assessments): {len(batch1)} files")
        print(f"  Batch 2 (READMEs): {len(batch2)} files")
        print(f"  Batch 3 (HTML + Docs): {len(batch3)} files")
        print(f"  Total: {len(batch1) + len(batch2) + len(batch3)} files\n")

        self.stats['files_by_batch'] = {
            'batch1': len(batch1),
            'batch2': len(batch2),
            'batch3': len(batch3)
        }

        return batch1, batch2, batch3

    def process_file(self, filepath: Path) -> Dict:
        """
        Process a single file and return transformation stats.

        Args:
            filepath: Path to file to process

        Returns:
            Dictionary with processing results
        """
        result = {
            'path': str(filepath),
            'processed': False,
            'indicators_found': 0,
            'indicators_removed': 0,
            'error': None
        }

        try:
            # Read original content
            with open(filepath, 'r', encoding='utf-8') as f:
                original = f.read()

            # Scan for indicators
            indicators = self.humanizer.scan_file(str(filepath))

            # Count indicators above threshold
            high_conf_indicators = {}
            for pattern_name, pattern_indicators in indicators.items():
                high_conf = [ind for ind in pattern_indicators
                            if ind.confidence >= self.confidence_threshold]
                if high_conf:
                    high_conf_indicators[pattern_name] = high_conf

            total_indicators = sum(len(inds) for inds in high_conf_indicators.values())
            result['indicators_found'] = total_indicators

            if total_indicators == 0:
                # No indicators to remove
                self.stats['skipped_files'] += 1
                return result

            # Apply transformations
            transformed = self.humanizer.apply_transforms(
                original,
                self.confidence_threshold
            )

            # Write transformed content
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(transformed)

            result['processed'] = True
            result['indicators_removed'] = total_indicators
            self.stats['processed_files'] += 1
            self.stats['total_indicators'] += total_indicators

            # Track indicator types
            for pattern_name, pattern_indicators in high_conf_indicators.items():
                self.stats['indicators_by_type'][pattern_name] += len(pattern_indicators)

            # Store sample transformations (first 5)
            if len(self.stats['sample_transformations']) < 5:
                self.stats['sample_transformations'].append({
                    'file': filepath.name,
                    'indicators': list(high_conf_indicators.keys()),
                    'count': total_indicators
                })

        except Exception as e:
            result['error'] = str(e)
            self.stats['error_files'] += 1
            print(f"  ERROR processing {filepath.name}: {e}")

        return result

    def git_commit(self, files: List[Path], message: str):
        """Create a git commit for the specified files."""
        try:
            # Add files
            file_paths = [str(f) for f in files]
            subprocess.run(['git', 'add'] + file_paths, check=True, cwd='/home/coolhand')

            # Commit
            subprocess.run(
                ['git', 'commit', '-m', message],
                check=True,
                cwd='/home/coolhand'
            )
            print(f"  ✓ Committed: {message}")
        except subprocess.CalledProcessError as e:
            print(f"  ERROR committing: {e}")

    def process_batch1(self, files: List[Path]):
        """Process Batch 1: Assessment reports with individual commits."""
        print("\n" + "="*70)
        print(f"BATCH 1: Processing {len(files)} assessment reports (individual commits)")
        print("="*70)

        processed_count = 0
        for i, filepath in enumerate(files, 1):
            print(f"[{i}/{len(files)}] Processing {filepath.name}...")

            result = self.process_file(filepath)

            if result['processed']:
                # Individual commit for each file
                commit_msg = f"humanize: remove AI indicators from {filepath.name}"
                self.git_commit([filepath], commit_msg)
                processed_count += 1
            elif result['error']:
                print(f"  Skipped due to error")
            else:
                print(f"  Skipped (no indicators found)")

        print(f"\nBatch 1 Complete: {processed_count}/{len(files)} files processed")

    def process_batch2(self, files: List[Path]):
        """Process Batch 2: READMEs with single batch commit."""
        print("\n" + "="*70)
        print(f"BATCH 2: Processing {len(files)} project READMEs (single commit)")
        print("="*70)

        processed_files = []

        for i, filepath in enumerate(files, 1):
            print(f"[{i}/{len(files)}] Processing {filepath.name}...")

            result = self.process_file(filepath)

            if result['processed']:
                processed_files.append(filepath)
            elif result['error']:
                print(f"  Skipped due to error")
            else:
                print(f"  Skipped (no indicators found)")

        # Single commit for all processed files
        if processed_files:
            commit_msg = f"humanize: batch-2 complete - project READMEs ({len(processed_files)} files)"
            self.git_commit(processed_files, commit_msg)

        print(f"\nBatch 2 Complete: {len(processed_files)}/{len(files)} files processed")

    def process_batch3(self, files: List[Path]):
        """Process Batch 3: HTML and docs with single batch commit."""
        print("\n" + "="*70)
        print(f"BATCH 3: Processing {len(files)} HTML and public docs (single commit)")
        print("="*70)

        processed_files = []

        for i, filepath in enumerate(files, 1):
            print(f"[{i}/{len(files)}] Processing {filepath.name}...")

            result = self.process_file(filepath)

            if result['processed']:
                processed_files.append(filepath)
            elif result['error']:
                print(f"  Skipped due to error")
            else:
                print(f"  Skipped (no indicators found)")

        # Single commit for all processed files
        if processed_files:
            commit_msg = f"humanize: batch-3 complete - HTML and public docs ({len(processed_files)} files)"
            self.git_commit(processed_files, commit_msg)

        print(f"\nBatch 3 Complete: {len(processed_files)}/{len(files)} files processed")

    def generate_report(self) -> str:
        """Generate comprehensive processing report."""
        duration = (datetime.now() - self.start_time).total_seconds()

        report = f"""# Documentation Humanization Report

**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Duration**: {duration:.1f} seconds
**Confidence Threshold**: {self.confidence_threshold}

## Summary

- **Total Files Discovered**: {self.stats['total_files']}
- **Files Processed**: {self.stats['processed_files']}
- **Files Skipped**: {self.stats['skipped_files']} (no indicators found)
- **Files with Errors**: {self.stats['error_files']}
- **Total Indicators Removed**: {self.stats['total_indicators']}

## Batch Breakdown

| Batch | Description | Files |
|-------|-------------|-------|
| Batch 1 | Assessment Reports | {self.stats['files_by_batch']['batch1']} |
| Batch 2 | Project READMEs | {self.stats['files_by_batch']['batch2']} |
| Batch 3 | HTML + Public Docs | {self.stats['files_by_batch']['batch3']} |

## Indicators Removed by Type

"""

        if self.stats['indicators_by_type']:
            for pattern_name, count in sorted(
                self.stats['indicators_by_type'].items(),
                key=lambda x: x[1],
                reverse=True
            ):
                report += f"- **{pattern_name.replace('_', ' ').title()}**: {count}\n"
        else:
            report += "No indicators found.\n"

        report += "\n## Sample Transformations\n\n"

        if self.stats['sample_transformations']:
            for i, sample in enumerate(self.stats['sample_transformations'], 1):
                report += f"{i}. **{sample['file']}**\n"
                report += f"   - Indicators removed: {sample['count']}\n"
                report += f"   - Types: {', '.join(sample['indicators'])}\n\n"
        else:
            report += "No transformations applied.\n"

        report += f"""
## Performance Metrics

- **Processing Rate**: {self.stats['total_files'] / duration:.1f} files/second
- **Average Indicators per File**: {self.stats['total_indicators'] / max(self.stats['processed_files'], 1):.1f}

## Git Strategy

- **Batch 1**: Individual commits per file
- **Batch 2**: Single batch commit
- **Batch 3**: Single batch commit

## Next Steps

Files flagged for manual review: {self.stats['error_files']}

---

*Generated by DocumentHumanizer*
*Author: Luke Steuber*
"""

        return report


def main():
    """Main execution entry point."""
    print("\n" + "="*70)
    print("DOCUMENTATION HUMANIZATION PROCESS")
    print("="*70)

    # Initialize processor
    processor = BatchDocumentProcessor(confidence_threshold=0.8)

    # Discover files
    batch1, batch2, batch3 = processor.discover_files()
    processor.stats['total_files'] = len(batch1) + len(batch2) + len(batch3)

    # Create checkpoint before batch 1
    print("\nCreating checkpoint before batch 1...")
    try:
        subprocess.run(
            ['git', 'add', '-A'],
            check=True,
            cwd='/home/coolhand'
        )
        subprocess.run(
            ['git', 'commit', '-m', 'checkpoint: before batch-1 humanization'],
            check=True,
            cwd='/home/coolhand'
        )
        print("✓ Checkpoint created\n")
    except subprocess.CalledProcessError:
        print("(No changes to checkpoint)\n")

    # Process batches
    processor.process_batch1(batch1)
    processor.process_batch2(batch2)
    processor.process_batch3(batch3)

    # Generate report
    print("\n" + "="*70)
    print("GENERATING REPORT")
    print("="*70)

    report = processor.generate_report()

    # Save report
    report_dir = Path('/home/coolhand/geepers/reports/by-date/2026-01-05')
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / 'humanizer-complete.md'

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n✓ Report saved to: {report_path}")
    print("\n" + report)

    print("\n" + "="*70)
    print("HUMANIZATION COMPLETE")
    print("="*70)
    print(f"Total files processed: {processor.stats['processed_files']}")
    print(f"Total indicators removed: {processor.stats['total_indicators']}")
    print("="*70 + "\n")


if __name__ == '__main__':
    main()
