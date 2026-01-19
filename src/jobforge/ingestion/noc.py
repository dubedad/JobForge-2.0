"""DIM NOC table ingestion."""

from pathlib import Path
from typing import Optional

import polars as pl

from jobforge.ingestion.transforms import derive_unit_group_id, filter_unit_groups
from jobforge.pipeline.config import PipelineConfig
from jobforge.pipeline.engine import PipelineEngine


def ingest_dim_noc(
    source_path: Path,
    config: Optional[PipelineConfig] = None,
    table_name: str = "dim_noc",
) -> dict:
    """Ingest NOC structure CSV to gold layer as DIM NOC.

    Transforms applied:
    - Bronze: Rename columns to snake_case, cast Level to Int32
    - Silver: Filter to Level 5 (unit groups), derive unit_group_id
    - Gold: Final column selection

    Args:
        source_path: Path to NOC structure CSV file.
        config: Pipeline configuration (defaults to PipelineConfig()).
        table_name: Output table name (defaults to "dim_noc").

    Returns:
        Dict with gold_path, batch_id, and row counts.
    """
    engine = PipelineEngine(config=config)

    # Bronze schema: rename columns to snake_case, cast types
    bronze_schema = {
        "rename": {
            "Level": "level",
            "Hierarchical structure": "hierarchical_structure",
            "Code - NOC 2021 V1.0": "noc_code",
            "Class title": "class_title",
            "Class definition": "class_definition",
        },
        "cast": {
            "level": pl.Int32,
        },
    }

    # Silver transforms: filter to unit groups, derive unit_group_id
    silver_transforms = [
        filter_unit_groups,
        derive_unit_group_id,
    ]

    # Gold transforms: select final columns
    def select_dim_noc_columns(df: pl.LazyFrame) -> pl.LazyFrame:
        """Select and order columns for DIM NOC gold table."""
        return df.select(
            [
                "unit_group_id",
                "noc_code",
                "class_title",
                "class_definition",
                "hierarchical_structure",
                # Provenance columns are preserved automatically
                "_source_file",
                "_ingested_at",
                "_batch_id",
                "_layer",
            ]
        )

    result = engine.run_full_pipeline(
        source_path=source_path,
        table_name=table_name,
        domain="noc",
        bronze_schema=bronze_schema,
        silver_transforms=silver_transforms,
        gold_transforms=[select_dim_noc_columns],
    )

    return result


if __name__ == "__main__":
    # Quick manual test
    import sys

    if len(sys.argv) > 1:
        source = Path(sys.argv[1])
    else:
        source = Path("data/source/noc_structure_en.csv")

    result = ingest_dim_noc(source)
    print(f"Ingested to: {result['gold_path']}")
    print(f"Rows: {pl.read_parquet(result['gold_path']).shape[0]}")
