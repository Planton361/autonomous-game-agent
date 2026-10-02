"""Content-safe reuse for immutable synthetic projection acceptance fixtures."""

import pytest

from fh_agent.research_atlas import private_views as views


@pytest.fixture(scope="module", autouse=True)
def cached_full_projections():
    """Keep changed/order-permuted inputs live; copy only immutable byte outputs.

    No filesystem state is cached: callers still read source bytes and construct
    current snapshots. Exact input order is part of the key, so order-invariance
    assertions independently exercise the production renderer on each ordering.
    """
    render = views.reference_views_tree
    cache = {}

    def tree(
        commit,
        public_base,
        direct_base,
        reference,
        atlas,
        locators,
        snapshot,
        source_projection_present,
        private_records=(),
        *,
        engineering_bindings=(),
        source_catalog=None,
    ):
        key = (
            commit,
            public_base,
            direct_base,
            reference.model_dump_json(),
            atlas.source_atlas_schema,
            tuple((identity, node.model_dump_json()) for identity, node in atlas.entities.items()),
            tuple(edge.model_dump_json() for edge in atlas.relationships),
            tuple((identity, str(path)) for identity, path in locators.items()),
            snapshot.model_dump_json(),
            source_projection_present,
            tuple(record.model_dump_json() for record in private_records),
            tuple(binding.model_dump_json() for binding in engineering_bindings),
            source_catalog.model_dump_json() if source_catalog is not None else None,
        )
        if key not in cache:
            cache[key] = render(
                commit,
                public_base,
                direct_base,
                reference,
                atlas,
                locators,
                snapshot,
                source_projection_present,
                private_records,
                engineering_bindings=engineering_bindings,
                source_catalog=source_catalog,
            )
        return dict(cache[key])

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(views, "reference_views_tree", tree)
        yield
