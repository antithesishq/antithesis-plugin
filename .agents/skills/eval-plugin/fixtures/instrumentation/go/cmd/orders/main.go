package main

import (
	"shop/internal/work"

	"github.com/antithesishq/antithesis-sdk-go/assert"
)

func main() {
	work.Spin(4)
	assert.Reachable("orders started", nil)
	select {}
}
