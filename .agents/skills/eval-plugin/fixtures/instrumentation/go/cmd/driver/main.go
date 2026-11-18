// The driver reports setup complete and holds the test template; it has no workload.
package main

import (
	"instrfixture/internal/work"

	"github.com/antithesishq/antithesis-sdk-go/assert"
	"github.com/antithesishq/antithesis-sdk-go/lifecycle"
)

func main() {
	work.Spin(2)
	lifecycle.SetupComplete(map[string]any{"component": "driver"})
	assert.Reachable("driver started", nil)
	select {}
}
