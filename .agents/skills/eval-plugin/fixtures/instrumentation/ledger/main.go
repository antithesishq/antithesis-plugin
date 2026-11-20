package main

import (
	"time"

	"github.com/antithesishq/antithesis-sdk-go/assert"
)

func main() {
	assert.Reachable("ledger started", nil)
	x := 1
	for {
		if x%2 == 0 {
			x = x/2 + 3
		} else {
			x = 3*x + 1
		}
		x %= 100003
		time.Sleep(50 * time.Millisecond)
	}
}
