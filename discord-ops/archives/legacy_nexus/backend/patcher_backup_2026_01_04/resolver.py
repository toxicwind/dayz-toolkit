import logging

log = logging.getLogger("patch_resolver")


class PatchResolver:
    def __init__(self, raw_patches):
        self.raw_patches = raw_patches

    def resolve(self):
        """
        Sort patches. For now, we trust the order in manifest or just return as is.
        Ideally we'd topo-sort if we had dependencies.
        """
        # Return list of patch dicts
        return self.raw_patches

    def validate_enabled_chain(self, sorted_patches):
        """
        Filter enabled patches.
        """
        enabled = []
        for p in sorted_patches:
            if p.get("enabled", True):
                enabled.append(p)
        return enabled
