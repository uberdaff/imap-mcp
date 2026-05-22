### Plan to Add Custom Date Search Support to the IMAP MCP Server

Based on the code analysis, the `search_emails` tool in `imap_mcp/tools.py` needs modifications to parse and apply custom IMAP search queries (like date ranges) instead of ignoring the `query` parameter for most criteria. Here's a step-by-step plan:

#### 1. **Understand Current Limitations**
   - The tool only uses `query` for text-based searches (e.g., `criteria="text"`).
   - For `criteria="all"`, it ignores `query` and searches all emails, returning the 10 most recent (by UID).
   - No support for IMAP date keywords like `SINCE`, `ON`, `BEFORE`, `SENTSINCE`, etc.
   - The `imap_client.py` `search` method can handle lists of criteria (e.g., `["SINCE", "8-Aug-2022"]`), but the tool doesn't leverage this for custom queries.

#### 2. **Key Changes Needed**
   - **Modify `search_emails` in `tools.py`**:
     - Add logic to parse the `query` string into an IMAP criteria list when `criteria="all"`.
     - If parsing succeeds, use the parsed criteria; otherwise, fall back to "ALL".
     - Update the function docstring and parameter descriptions.
   - **Add a simple query parser**:
     - Split the query string by spaces and handle basic IMAP keywords.
     - Support common date formats (e.g., "8-Aug-2022").
   - **Ensure backward compatibility**:
     - Existing calls (e.g., `criteria="text"`) should work unchanged.
     - New calls can use `criteria="all"` with `query="SINCE 8-Aug-2022"`.

#### 3. **Implementation Steps**
   - **Step 1: Create a query parser function**
     - Add a helper function `parse_imap_query(query: str) -> Optional[List[str]]` in `tools.py`.
     - It should split the query and validate basic IMAP syntax (e.g., check for known keywords).
     - Example: `"SINCE 8-Aug-2022 BEFORE 15-Aug-2022"` → `["SINCE", "8-Aug-2022", "BEFORE", "15-Aug-2022"]`
     - Return `None` if invalid, to fall back to "ALL".

   - **Step 2: Update `search_emails` logic**
     - After getting `search_criteria` from the map, check if `criteria == "all"` and `query` is provided.
     - If so, call `parse_imap_query(query)` and use the result if valid.
     - Example code snippet:
       ```python
       if criteria.lower() == "all" and query:
           parsed_criteria = parse_imap_query(query)
           if parsed_criteria:
               search_criteria = parsed_criteria
       ```

   - **Step 3: Handle date formats**
     - Ensure dates are in IMAP format (DD-MMM-YYYY, e.g., "08-Aug-2022").
     - The `imapclient` library handles date parsing internally.

   - **Step 4: Update limits and sorting**
     - Keep the `limit` parameter, but note that for large result sets, it may need adjustment.
     - Sorting by UID assumes higher UIDs are newer, which may not hold for all servers—consider sorting by actual date if possible.

   - **Step 5: Testing**
     - Test with queries like `query="ON 08-Aug-2022"`, `query="SINCE 01-Aug-2022 BEFORE 31-Aug-2022"`.
     - Verify it returns correct results without breaking existing functionality.
     - Check edge cases (invalid queries, empty results).

#### 4. **Potential Risks and Considerations**
   - **Security**: Ensure parsed queries don't allow malicious input (e.g., limit to known IMAP keywords).
   - **Performance**: Date searches on large mailboxes may be slow; consider adding warnings for broad ranges.
   - **IMAP Server Compatibility**: Not all servers support all search criteria—test with your provider (netlife.no).
   - **Dependencies**: Relies on `imapclient` for search; no changes needed there.
   - **Fallback**: If parsing fails, log a warning and use "ALL" to avoid breaking.

#### 5. **Estimated Effort**
   - Code changes: ~50-100 lines in `tools.py`.
   - Testing: 1-2 hours with sample queries.
   - Total time: 2-4 hours.

#### 6. **Next Steps**
   - If you approve, I can implement these changes directly in the code.
   - Alternatively, provide more details on desired query formats or edge cases.