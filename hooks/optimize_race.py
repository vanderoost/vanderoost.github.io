"""Fix a thread race in Material's "optimize" plugin (mkdocs-material 9.7.7).

OptimizePlugin.on_env hands each image to a worker thread and only then calls
files.remove(file) on the main thread. On a cache hit the worker finishes
almost at once and points the file at its copy in .cache/plugin/optimize/,
which changes its src_uri. If that wins the race, files.remove() no longer
finds the file and the build dies with

    ValueError: '.cache/plugin/optimize/....png' not in collection

It only happens some of the time, and mostly in CI, where actions/cache
restores a warm .cache. The replacement below is the same method with the two
steps swapped: the file leaves the collection first, then the job starts.

Hooks are imported when the config loads, before any build event, so the patch
is in place by the time on_env runs. Recheck it when bumping mkdocs-material:
if upstream fixes the order, delete this file and its line in mkdocs.yml.
"""

import os

from material.plugins.optimize.plugin import OptimizePlugin


def _on_env(self, env, *, config, files):
    if not self.config.enabled or not self.config.optimize:
        return

    for file in files.media_files():
        if self._is_excluded(file):
            continue

        # Remove before submitting: the job may rewrite file.src_path
        files.remove(file)

        path = os.path.join(self.config.cache_dir, file.src_path)
        self.pool_jobs[file.abs_src_path] = self.pool.submit(
            self._optimize_image, file, path, config
        )


OptimizePlugin.on_env = _on_env
