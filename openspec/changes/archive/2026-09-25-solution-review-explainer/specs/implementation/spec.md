## ADDED Requirements

### Requirement: The delivered change is explained for solution review
When `wait_for_pr` settles the head or the review loop escalates, the implementing run SHALL
end with a plain-words explanation of the delivered change, published as a page linked in the
final message, or written in that message when the carrier cannot publish a page.

#### Scenario: Run ends
- **WHEN** the implementing run stops after its PR
- **THEN** its final message links or carries the plain-words explanation of the delivered change
