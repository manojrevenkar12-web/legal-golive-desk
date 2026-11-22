# 2. The permission audit compares two readings of the same DMS

**Status:** accepted

A legal AI workspace that indexes iManage or SharePoint must never let a user find a document the DMS denies them,
above all across an ethical wall. The audit computes readers per document twice: as the DMS means it (nested groups
fully expanded, walls applied at full depth, "anyone" links not treated as firm-wide) and as the planned connector would
read it (its group depth, whether walls are mapped, how links are treated, or one index for every user). Every extra
user-document pair is an exposure and blocks go-live; every missing pair is a document lawyers will not find.

Each exposure is attributed to the first planned setting that explains it, so the fix is named, not guessed.
