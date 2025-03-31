from invoke import Collection

from tasks import dev, stubs

ns = Collection(
    dev, stubs, fl=dev.format_and_lint, tests=dev.tests, stubgen=stubs.bindings
)
