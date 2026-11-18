package main

import (
	"instrfixture/internal/work"

	"github.com/antithesishq/antithesis-sdk-go/assert"
)

func main() {
	work.Spin(4)
	assert.Reachable("go worker started", nil)
	select {}
}
