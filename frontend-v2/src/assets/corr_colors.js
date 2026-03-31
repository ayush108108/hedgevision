/* assets/corr_colors.js
   Map a correlation value ∈ [-1,1] → brand colour.
   Expose as window.dashAgGridFunctions.corrCellStyle 
*/

window.dashAgGridFunctions = Object.assign(
    window.dashAgGridFunctions || {},
    {
        corrCellStyle: params => {
            // Skip empty / diagonal cells
            if (params.value === null || params.value === undefined) return {};

            // --- BEGIN DEBUG ---
            console.log("corrCellStyle params.value:", params.value, "Type:", typeof params.value);
            // --- END DEBUG ---

            const v = Number(params.value);

             ----- 5-stop brand palette ----- 
            let bg;                // background colour
            if (v <= -0.75) bg = '#313695';          // strong negative
            else if (v <= -0.25) bg = '#74add1';     // moderate negative
            else if (v <=  0.25) bg = '#f7f7f7';     // neutral
            else if (v <=  0.75) bg = '#f46d43';     // moderate positive
            else                  bg = '#67001f';    // strong positive

            /* optional: white font on dark cells */
            const font = (v <= -0.75 || v >= 0.75) ? '#ffffff' : '#000000';

            return {
                backgroundColor: bg,
                color: font,
                textAlign: 'center',
                fontWeight: '500'
            };
        }
    }
);
 