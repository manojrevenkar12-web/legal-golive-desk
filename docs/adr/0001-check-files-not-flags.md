# 1. Check the customer's files, not flags

**Status:** accepted

The world could tell the product "this customer has an expiring certificate". It does not. It writes the SAML metadata
with a real X.509 certificate, the OIDC discovery document, the DMS permission export and the tenant plan, and the
product's checkers read those files exactly as they would read a customer's. Recall against planted problems is then a
test of the checkers' code, and the same checkers serve the API.

Consequence: recall is 100% by construction for the problems the world knows how to plant. It says nothing about problem
kinds the world never plants. The README says so.
