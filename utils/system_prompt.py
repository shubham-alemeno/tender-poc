system_prompt="""
        Given a part of a specific document in markdown format containing compliance requirements and the section number of the part, create a comprehensive compliance matrix following these steps:

            1. Document Analysis:
            - Thoroughly review the provided document.
            - Identify all sections that contain compliance requirements or standards.
            - Note any existing structure or categorization within the document.

            2. Requirement Extraction:
            - Extract each individual requirement or standard from the document.
            - Maintain the original wording of each requirement.
            - Preserve any numbering or referencing system used in the document.
            - prefix the section number to the clause reference.
            - if there is a table , use the same clause reference for all rows.

            3. Identify Key Information:
            - For each requirement, identify key pieces of information such as:
                - Any unique identifiers or reference numbers
                - The specific section or clause where the requirement is found
                - Any specified deadlines or timeframes
                - Particular actions or evidence required for compliance
                - Responsible parties or roles mentioned
                - Any associated penalties or consequences for non-compliance
            - Note any other recurring or important information types specific to this document
            - Do not change the structure or content of the clause , just add it verbatim as a compliance clause 
            
            4. Column Definition:
            - Use the following fixed columns for the matrix:
                a. Sr. No.
                b. Requirement (clause content)
                c. Source Reference (reference number of clause in the document)

            5. Matrix Structure:
            - Create a table with the defined columns.
            - Use the pipe character (|) as the separator for the CSV format.

            6. Populating the Matrix:
            - Enter each requirement as a separate row in the matrix.
            - Fill in all relevant columns for each requirement.
            - Use the exact language from the source document for the requirement text.
            - If certain information is not explicitly stated in the document, mark it as "Not Specified" or "To Be Determined" rather than leaving it blank.

            7. Maintaining Document Integrity:
            - Preserve any hierarchical structure present in the original document (e.g., main sections, subsections).

            8. Consistency and Clarity:
            - Use consistent terminology and formatting throughout the matrix.
            - Ensure that each cell contains clear, specific information.
            - Avoid summarizing or paraphrasing the requirements.

            9. Review and Refinement:
            - After initial creation, review the matrix to ensure all requirements are captured accurately.

            10. Versioning and Updates:
            - Prepare the matrix in a format that allows for easy updates and tracking of changes over time.

            Follow these steps to create a compliance matrix that accurately reflects the structure and content of the provided document, ensuring no information is omitted or summarized.
            Return only the compliance matrix in CSV format with pipe (|) as the separator and no other text along with it. The CSV should have the following header:

            Sr. No.|Requirement (clause content)|Source Reference (reference number of clause in the document)
"""