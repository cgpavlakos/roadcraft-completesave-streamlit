import zlib
import hashlib
import json
import streamlit as st
import os # For checking default file path existence

# --- Constants ---
WBITS_VALUE = -15
HEADER_LENGTH = 53
ZLIB_HEADER = b'\x78\x9c'

# List of all levels to unlock
ALL_LEVELS_LIST = [
    "rb_map_01_storm_preparation",
    "rb_map_07_rail_failure",
    "rb_map_08_contamination",
    "rb_map_02_storm_aftermath",
    "rb_map_03_incommunicado",
    "rb_map_04_salt_mines",
    "rb_map_05_dam_break",
    "rb_map_06_sinkholes",
    "rb_map_09_sand_storm",
    "rb_map_10_geothermal"
]

# List of all trucks to unlock
ALL_TRUCKS_LIST = [
      "aramatsu_bowhead_heavy_dumptruck_new",
      "kronenwerk_l34_dozer_old",
      "kronenwerk_l34_dozer_res",
      "baikal_5916_crane_res",
      "baikal_5916_crane_old",
      "mule_t1_cargo_old",
      "mule_t1_cargo_res",
      "baikal_65206_heavy_dumptruck_res",
      "baikal_65206_heavy_dumptruck_old",
      "mule_t1_crane_cargo_res",
      "zikz_612c_heavy_crane_res",
      "zikz_612c_heavy_crane_old",
      "azov_4317dl_cargo_res",
      "wayfarer_st7050_cargo_main",
      "kronenwerk_l34_cargo_dozer_res",
      "vostok_tk53krot_cable_layer_res",
      "vostok_tk53krot_cable_layer_old",
      "mtk_100m_stump_mulcher_old",
      "mtk_100m_stump_mulcher_res",
      "greenway_740cross_cargo_new",
      "kronenwerk_l34_wood_grabber_res",
      "kronenwerk_l34_forwarder_res",
      "epec_tc305_heavy_crane_new",
      "zikz_605e_heavy_transporter_res",
      "base_tayga_6455b_dumptruck_res",
      "base_baikal_65206_heavy_dumptruck_old",
      "tayga_6455b_dumptruck_res",
      "mtk_proseka200_cargo_res",
      "tuz_119lynx_scout_old",
      "base_mtk_100m_stump_mulcher_old",
      "aramatsu_crayfish_wood_grapple_new",
      "base_voron_3327_cargo_old",
      "base_tayga_6455b_dumptruck_old",
      "base_ds_135bunker_paver_res",
      "epec_lt200_crane_cargo_new",
      "mtk_proseka200_forwarder_old",
      "base_khan_lo_strannik_mob_old",
      "vostok_atm53pioneer_dozer_old",
      "mtk_proseka200_forwarder_res",
      "vostok_atm53pioneer_dozer_res",
      "base_baikal_5916_crane_old",
      "tuz_303karelian_scout_res",
      "epec_hwc945_heavy_crane_new",
      "arling_120special_paver_new",
      "base_kronenwerk_l34_dozer_old",
      "mtk_md76_harvester_old",
      "ds_135bunker_paver_res",
      "don_72malamute_scout_new",
      "mtk_md76_harvester_res",
      "arling_750r_roller_new",
      "base_mtk_md76_harvester_old",
      "base_vostok_atm53pioneer_dozer_res",
      "mtk_md76_wood_grapple_res",
      "base_zikz_612c_heavy_crane_old",
      "aramatsu_crayfish_harvester_new",
      "warden_kochevnik_mob_new",
      "epec_lt200_dumptruck_new",
      "base_tuz_119lynx_scout_old",
      "base_don_72malamute_scout_new",
      "base_voron_3327_cargo_res",
      "base_tuz_303karelian_scout_old",
      "base_ds_55katok_roller_old",
      "ds_55katok_roller_res",
      "base_epec_lt200_dumptruck_new",
      "tuz_119lynx_scout_res",
      "base_arling_120special_paver_new",
      "base_mtk_proseka200_forwarder_old",
      "base_ds_135bunker_paver_old",
      "base_zikz_605e_mobile_scalper_res",
      "vostok_etv89_crane_new",
      "voron_3327_cargo_res",
      "epec_tc305_heavy_crane_grabber_new",
      "base_mtk_md76_wood_grapple_res",
      "greenway_740cross_forwarder_new",
      "tuz_303karelian_scout_old",
      "step_pike_light_transporter_res",
      "zikz_605e_mobile_scalper_res",
      "base_arling_750r_roller_new",
      "base_mtk_md76_harvester_old",
      "base_epec_hwc945_heavy_crane_new",
      "base_zikz_605e_heavy_transporter_old",
      "aramatsu_kite3_stump_mulcher_new",
      "base_vostok_atm53pioneer_dozer_old",
      "base_vostok_tk53krot_cable_layer_old",
      "base_step_pike_light_transporter_old",
      "base_mule_t1_cargo_old"
]
# --- Utility Functions ---
def compute_md5(data):
    """Compute the MD5 hash of the given data."""
    md5_hash = hashlib.md5(data).hexdigest()
    return md5_hash

def try_decompress_zlib_block(data, start_offset=0):
    """Try different decompression methods on the data starting at offset."""
    result = {}
    zlib_block = data[start_offset:]
    uncompressed_size = int.from_bytes(zlib_block[:4], byteorder='little')
    compressed_size = int.from_bytes(zlib_block[4:8], byteorder='little')

    # Confirm next 2 bytes are zlib header (or expected for raw deflate)
    # The original WBITS_VALUE = -15 means raw deflate, so there's no zlib header
    # But it's good to keep the check if the game sometimes uses standard zlib
    if zlib_block[8:10] == ZLIB_HEADER:
        st.warning("Warning: Standard zlib header found. Ensure WBITS_VALUE=-15 is correct for raw deflate.")
    
    # Decompress from here
    decompressed = zlib.decompress(zlib_block[10:], wbits=WBITS_VALUE)

    result['uncompressed_size'] = uncompressed_size
    result['compressed_size'] = compressed_size
    result['decompressed_bytes'] = decompressed
    return result

def decode_file(file_content_bytes):
    """Decode a file by decompressing its zlib blocks and return a single byte array."""
    if not file_content_bytes:
        return None, None

    # st.write(f"File size: {len(file_content_bytes)} bytes") # Commented out to avoid cluttering UI

    md5 = compute_md5(file_content_bytes[HEADER_LENGTH:])
    # st.write(f"Original MD5 hash of compressed data from offset {HEADER_LENGTH}: {md5}")

    offset = HEADER_LENGTH
    decompressed_data = bytearray()

    try:
        while offset < len(file_content_bytes):
            result = try_decompress_zlib_block(file_content_bytes, start_offset=offset)
            decompressed_data.extend(result['decompressed_bytes'])
            offset += result['compressed_size'] + 8 # 8 bytes for the 2 int32s
    except zlib.error as e:
        st.error(f"Zlib decompression error: {e}. The file might be corrupted or not a valid save file.")
        return None, None
    except Exception as e:
        st.error(f"Error during file decoding: {e}")
        return None, None
    
    # st.write(f"Total decompressed data size: {len(decompressed_data)} bytes")
    return file_content_bytes, decompressed_data

def encode_file(original_file_content, decompressed_data_edited):
    """Encode a file by compressing the decompressed data into chunks."""
    try:
        st.info("Rebuilding the file with the new compressed data...")

        new_zlib_data = b''
        chunk_size = 1024**2 # 1 MB (1MB chunks for compression)
        offset = 0

        while offset < len(decompressed_data_edited):
            chunk = decompressed_data_edited[offset:offset + chunk_size]
            offset += chunk_size

            new_block_uncompressed_size_bytes = len(chunk).to_bytes(4, 'little')
            
            # Using WBITS_VALUE=-15 for raw deflate stream, as per original code's design
            new_compressed_data = zlib.compress(chunk, level=-1, wbits=WBITS_VALUE) 
            
            adler32 = zlib.adler32(chunk)
            adler32_bytes = adler32.to_bytes(4, 'big')

            new_block_compressed_size = len(new_compressed_data) + 6
            new_block_compressed_size_bytes = new_block_compressed_size.to_bytes(4, 'little')

            # Append the new block to the new data
            new_zlib_data += new_block_uncompressed_size_bytes + new_block_compressed_size_bytes + ZLIB_HEADER + new_compressed_data + adler32_bytes

        # Rebuild header components
        original_filetype = original_file_content[:4]
        zero_bytes = b'\x00\x00\x00\x00'
        three_byte = b'\x03' # Constant byte from original header logic
        new_total_compressed_size_bytes = len(new_zlib_data).to_bytes(4, 'little')
        new_total_uncompressed_size_bytes = len(decompressed_data_edited).to_bytes(4, 'little')
        new_md5 = compute_md5(new_zlib_data)
        st.info(f"New MD5 hash of compressed data: {new_md5}")
        new_md5_bytes = new_md5.encode('utf-8')

        final_data = original_filetype + new_total_compressed_size_bytes + zero_bytes + new_total_uncompressed_size_bytes + zero_bytes + new_md5_bytes + three_byte + new_zlib_data

        # In Streamlit, we offer the file for download directly
        st.download_button(
            label="Download CompleteSave",
            data=final_data,
            file_name="CompleteSave",
            mime="application/octet-stream",
            help="Replace the original file in your save directory. **DID YOU BACK UP YOUR ORIGINAL?**"
        )
        st.success("File rebuilt and ready for download!")
        return True
    except Exception as e:
        st.error(f"Error during encoding: {e}. Please check the console/logs.")
        return False

# --- Streamlit App Layout and Logic ---

st.set_page_config(layout="centered", page_title="Roadcraft Save Editor", initial_sidebar_state="expanded")

st.title("Roadcraft Save Editor")
with st.sidebar:
    st.markdown("Upload and edit your CompleteSave file, usually found at: `%LocalAppData%\\Saber\\RoadCraftGame\\storage\\steam\\user\\<YOUR_STEAM_USER_ID>\\Main\\save`")
    st.markdown("The default steam deck location is: `/home/deck/.local/share/Steam/steamapps/compatdata/2104890/pfx/drive_c/users/steamuser/AppData/Local/Saber/RoadCraftGame/storage/steam/user/<YOUR_STEAM_USER_ID>/Main/save`")
    st.markdown("---")
    st.markdown("The source code for this app is available on [github](https://github.com/cgpavlakos/roadcraft-completesave-streamlit) if you prefer to run locally.")
    st.markdown("---") # Add a horizontal rule for visual separation
    st.markdown("If you find this useful, consider a small donation to my beer fund!")
    st.markdown(
        '<a href="https://coindrop.to/cgpavlakos" target="_blank">'
        '<img src="https://coindrop.to/embed-button.png" '
        'style="border-radius: 10px; height: 57px !important; width: 229px !important;" '
        'alt="Coindrop.to me">'
        '</a>',
        unsafe_allow_html=True
    )
    st.markdown("---")
    st.markdown("Thanks to NakedDevA for his [Roadcraft completesave editor](https://github.com/NakedDevA/roadcraft-completesave) which this is forked from.")

# Initialize session state variables if they don't exist
if 'json_data' not in st.session_state:
    st.session_state.json_data = None
if 'original_file_content_bytes' not in st.session_state:
    st.session_state.original_file_content_bytes = None
if 'initial_values' not in st.session_state:
    st.session_state.initial_values = {}
if 'initial_unlocked_levels_checkbox_state' not in st.session_state:
    st.session_state.initial_unlocked_levels_checkbox_state = False
if 'initial_unlocked_trucks_checkbox_state' not in st.session_state:
    st.session_state.initial_unlocked_trucks_checkbox_state = False
if 'initial_lift_fog_checkbox_state' not in st.session_state: # New state for fog of war
    st.session_state.initial_lift_fog_checkbox_state = False
if 'initial_remove_rusty_trucks_checkbox_state' not in st.session_state: # New state for removing rusty trucks
    st.session_state.initial_remove_rusty_trucks_checkbox_state = False


# --- File Loading Logic ---
# Define a function to load and initialize session state, to avoid repetition
def load_and_init_session_state(file_content):
    original_file_content_bytes, decompressed_data = decode_file(file_content)

    if original_file_content_bytes and decompressed_data:
        try:
            json_data = json.loads(decompressed_data.decode('utf-8'))
            st.session_state.json_data = json_data
            st.session_state.original_file_content_bytes = original_file_content_bytes
            
            # Initialize initial_values for the session
            st.session_state.initial_values = {
                'xp': json_data.get('SslValue', {}).get('xp', 0),
                'money': json_data.get('SslValue', {}).get('money', 0),
                'companyName': json_data.get('SslValue', {}).get('companyName', ""), 
                'recovery_coins': json_data.get('SslValue', {}).get('recoveryCoins', {}).get(next(iter(json_data.get('SslValue', {}).get('recoveryCoins', {})), ''), 0),
                'logs_4_idx': 0,
                'steel_beams_5_idx': 0,
                'concrete_6_idx': 0,
                'steel_pipes_7_idx': 0
            }

            # --- START NEW CODE ---
            # Initialize initial_values for hardmodeOptions
            hardmode_opts = json_data.get('SslValue', {}).get('hardmodeOptions', {})
            st.session_state.initial_values['hardmodeOptions'] = hardmode_opts.copy()
            # --- END NEW CODE ---

            # Populate initial_values for resources (using the correct keys)
            if 'fobsResources' in json_data.get('SslValue', {}):
                for map_data in json_data['SslValue']['fobsResources'].values():
                    if 'resources' in map_data and isinstance(map_data['resources'], list):
                        resources = map_data['resources']
                        if len(resources) > 4: st.session_state.initial_values['logs_4_idx'] = resources[4]
                        if len(resources) > 5: st.session_state.initial_values['steel_beams_5_idx'] = resources[5]
                        if len(resources) > 6: st.session_state.initial_values['concrete_6_idx'] = resources[6]
                        if len(resources) > 7: st.session_state.initial_values['steel_pipes_7_idx'] = resources[7]
                        break

            # --- Set initial state of unlock_levels checkbox ---
            current_unlocked_levels = json_data.get('SslValue', {}).get('unlockedLevels', [])
            st.session_state.initial_unlocked_levels_checkbox_state = all(level in current_unlocked_levels for level in ALL_LEVELS_LIST)

            # --- Set initial state of unlock_trucks checkbox ---
            current_unlocked_trucks = json_data.get('SslValue', {}).get('newUnlockedTrucks', [])
            st.session_state.initial_unlocked_trucks_checkbox_state = all(truck in current_unlocked_trucks for truck in ALL_TRUCKS_LIST)

            # --- Set initial state of lift_fog checkbox ---
            current_fog_progress = json_data.get('SslValue', {}).get('fogOfWarProgress', {})
            # Assume fog is lifted if all maps present have 100% progress
            st.session_state.initial_lift_fog_checkbox_state = all(progress == 100.0 for progress in current_fog_progress.values()) and bool(current_fog_progress)

            # --- Set initial state of remove_rusty_trucks checkbox ---
            # Check if any "old" trucks exist in storedTrucks, excluding "khan_lo_strannik_mob_old"
            current_stored_trucks = json_data.get('SslValue', {}).get('storedTrucks', {})
            has_rusty_trucks_to_remove = False
            for truck_name, truck_data in current_stored_trucks.items():
                if truck_name.endswith("_old") and truck_name != "khan_lo_strannik_mob_old" and len(truck_data) > 0:
                    has_rusty_trucks_to_remove = True
                    break
            st.session_state.initial_remove_rusty_trucks_checkbox_state = not has_rusty_trucks_to_remove # Checked if no removable rusty trucks are present

            st.success("File loaded successfully! Ready for editing.")
            st.rerun()
        except json.JSONDecodeError as e:
            st.error(f"Error decoding JSON from file: {e}. File might be corrupted.")
            # Reset session state on error
            st.session_state.json_data = None
            st.session_state.original_file_content_bytes = None
            st.session_state.initial_values = {}
        except Exception as e:
            st.error(f"An unexpected error occurred during file loading: {e}")
            st.session_state.json_data = None
            st.session_state.original_file_content_bytes = None
            st.session_state.initial_values = {}
    else:
        st.error("Failed to decode the file. It might not be a valid CompleteSave.")
        st.session_state.json_data = None
        st.session_state.original_file_content_bytes = None
        st.session_state.initial_values = {}


# --- File Uploader and Default Path Check ---
st.warning("BACK UP YOUR SAVES FIRST!!! This tool is unofficial, unsupported, and I have no way to help you if something breaks.")
st.markdown("---")
uploaded_file = st.file_uploader(
    "Upload your CompleteSave file:",
    type=None, # Allow any file type
    help="Browse for your CompleteSave file. Or, place 'CompleteSave' in the same directory as this script and restart."
)

default_file_path = "CompleteSave"

# 1. Check for default file if no file uploaded and no data loaded yet
if os.path.exists(default_file_path) and uploaded_file is None and st.session_state.json_data is None:
    try:
        with open(default_file_path, 'rb') as f:
            default_file_content = f.read()
        st.info(f"Attempting to load 'CompleteSave' from default path: '{default_file_path}'...")
        load_and_init_session_state(default_file_content)
    except Exception as e:
        st.error(f"Error loading default 'CompleteSave' file: {e}")

# 2. Process uploaded file if available and not already loaded
elif uploaded_file is not None and st.session_state.json_data is None:
    file_content_bytes = uploaded_file.read()
    st.info(f"Attempting to load uploaded file: '{uploaded_file.name}'...")
    load_and_init_session_state(file_content_bytes)


# --- Quick Edits Section (only show if data is loaded) ---
if st.session_state.json_data:
    st.subheader("Quick Edits")

    # Helper for status indicator and number input
    # This helper function now correctly retrieves the *current* value from json_data
    # and compares it against the *initial* value for the indicator.
    # It also handles the column layout for the input and its indicator.
    def create_number_input_with_status(label, widget_key, initial_value_key, parent_column, min_value=0, step=1):
        current_value_from_json = min_value # Default fallback

        # Logic to get the current value from st.session_state.json_data
        if initial_value_key == "xp":
            current_value_from_json = st.session_state.json_data.get('SslValue', {}).get('xp', min_value)
        elif initial_value_key == "money":
            current_value_from_json = st.session_state.json_data.get('SslValue', {}).get('money', min_value)
        elif initial_value_key == "recovery_coins":
            map_data_vals = st.session_state.json_data.get('SslValue', {}).get('recoveryCoins', {}).values()
            current_value_from_json = next(iter(map_data_vals), min_value)
        elif '_idx' in initial_value_key: # For resource indices
            resource_idx = int(initial_value_key.split('_')[-2])
            map_data_vals = st.session_state.json_data.get('SslValue', {}).get('fobsResources', {}).values()
            for map_data in map_data_vals:
                if 'resources' in map_data and isinstance(map_data['resources'], list) and len(map_data['resources']) > resource_idx:
                    current_value_from_json = map_data['resources'][resource_idx]
                    break
        
        # Create sub-columns within the parent_column for the input and its indicator
        # Adjust ratios to give enough space for label and input, plus a small space for icon
        input_sub_col, status_sub_col = parent_column.columns([0.85, 0.15]) 

        with input_sub_col:
            new_value = st.number_input(
                label=label,
                value=current_value_from_json,
                min_value=min_value,
                step=step,
                key=widget_key,
                help=f"Original: {st.session_state.initial_values.get(initial_value_key, 'N/A')}"
            )

        with status_sub_col:
            is_modified = (new_value != st.session_state.initial_values.get(initial_value_key, min_value))
            color = "red" if is_modified else "green"
            status_icon = f"<span style='color: {color}; font-size: 1.5em;'>&#x25CF;</span>"
            
            # Use st.markdown with a div to align the icon vertically with the input box
            # You might need to tweak margin-top based on exact browser/OS rendering
            st.markdown(f"<div style='margin-top: 25px;'>{status_icon}</div>", unsafe_allow_html=True) 

        return new_value # Only return the value, as rendering is handled internally
    
    # Helper for status indicator and string input
    def create_string_input_with_status(label, widget_key, initial_value_key, parent_column):
        current_value_from_json = st.session_state.json_data.get('SslValue', {}).get(initial_value_key, "")

        input_sub_col, status_sub_col = parent_column.columns([0.85, 0.15])

        with input_sub_col:
            new_value = st.text_input(
                label=label,
                value=current_value_from_json,
                key=widget_key,
                help=f"Original: {st.session_state.initial_values.get(initial_value_key, 'N/A')}"
            )

        with status_sub_col:
            is_modified = (new_value != st.session_state.initial_values.get(initial_value_key, ""))
            color = "red" if is_modified else "green"
            status_icon = f"<span style='color: {color}; font-size: 1.5em;'>&#x25CF;</span>"
            st.markdown(f"<div style='margin-top: 25px;'>{status_icon}</div>", unsafe_allow_html=True)
        
        return new_value

    # --- XP and Cash ---
    col1, col2 = st.columns(2) # Parent columns for XP and Cash sections
    xp_value = create_number_input_with_status("Experience Points (max = 605990)", "xp_input", "xp", parent_column=col1)
    cash_value = create_number_input_with_status("Cash", "money_input", "money", parent_column=col2)

    # --- Company Name ---
    company_name_col = st.columns(1)[0] # Single column for company name
    company_name_value = create_string_input_with_status("Company Name", "companyName_input", "companyName", parent_column=company_name_col)


    # --- Unlock All Levels Checkbox ---
    unlock_levels = st.checkbox(
        "Unlock All Levels",
        value=st.session_state.initial_unlocked_levels_checkbox_state, # Set default state based on loaded file
        key="unlock_all_levels_checkbox",
        help="Checking this will unlock all known levels in the game. If unchecked, no changes will be made to your available levels."
    )

    # --- Unlock All Trucks Checkbox ---
    unlock_trucks = st.checkbox(
        "Unlock All Trucks",
        value=st.session_state.initial_unlocked_trucks_checkbox_state, # Set default state based on loaded file
        key="unlock_all_trucks_checkbox",
        help="Checking this will unlock all known trucks in the game. If unchecked, no changes will be made to your available trucks."
    )

    # --- Remove Rusty Trucks Checkbox ---
    remove_rusty_trucks = st.checkbox(
        "Remove Rusty Trucks from Garage",
        value=st.session_state.initial_remove_rusty_trucks_checkbox_state, # Set default state based on loaded file
        key="remove_rusty_trucks_checkbox",
        help="Checking this will set the inventory count of all trucks ending in '_old' to zero, EXCEPT 'khan_lo_strannik_mob_old'. Trucks on maps will remain."
    )


    # # --- Lift all fog checkbox ---
    # lift_fog = st.checkbox(
    #     "Lift All Fog of War",
    #     value=st.session_state.initial_lift_fog_checkbox_state, # Set default state based on loaded file
    #     key="lift_fog_checkbox",
    #     help="Checking this will reveal all fog of war on all maps to 100%."
    # )


    st.subheader("Global Resources (applies to all maps)")

    # --- Recovery Coins ---
    rc_col_input, rc_col_status = st.columns([0.93, 0.07]) # Adjusted ratio for nearly full width input

    with rc_col_input:
        current_rc_value_from_json = st.session_state.json_data.get('SslValue', {}).get('recoveryCoins', {}).get(next(iter(st.session_state.json_data.get('SslValue', {}).get('recoveryCoins', {})), ''), 0)
        recovery_coins_value = st.number_input(
            label="Recovery Coins (Gas)",
            value=current_rc_value_from_json,
            min_value=0,
            step=1,
            key="recoveryCoins_input",
            help=f"Original: {st.session_state.initial_values.get('recovery_coins', 'N/A')}"
        )
    with rc_col_status:
        is_modified = (recovery_coins_value != st.session_state.initial_values.get('recovery_coins', 0))
        color = "red" if is_modified else "green"
        status_icon = f"<span style='color: {color}; font-size: 1.5em;'>&#x25CF;</span>"
        st.markdown(f"<div style='margin-top: 25px;'>{status_icon}</div>", unsafe_allow_html=True)

    
    # --- Logs, Steel Beams ---
    col3, col4 = st.columns(2) # Parent columns for Logs/SB sections
    logs_value = create_number_input_with_status("Logs", "logs_input", "logs_4_idx", parent_column=col3)
    steel_beams_value = create_number_input_with_status("Steel Beams", "steelBeams_input", "steel_beams_5_idx", parent_column=col4)

    # --- Concrete, Steel Pipes ---
    col5, col6 = st.columns(2) # Parent columns for Concrete/SP sections
    concrete_value = create_number_input_with_status("Concrete", "concrete_input", "concrete_6_idx", parent_column=col5)
    steel_pipes_value = create_number_input_with_status("Steel Pipes", "steelPipes_input", "steel_pipes_7_idx", parent_column=col6)


    # =================================================================
    # START: NEW CODE BLOCK for Hard Mode UI
    # =================================================================
    with st.expander("Hard Mode Settings", False):
        st.subheader("Hard Mode Tuning")

        # Check if the hardmodeOptions key exists before trying to build the UI
        hardmode_options = st.session_state.json_data.get("SslValue", {}).get("hardmodeOptions")

        if hardmode_options is not None:
            # Use columns for a cleaner layout
            hm_col1, hm_col2 = st.columns(2)
            
            with hm_col1:
                st.markdown("##### On/Off Toggles")
                # Create toggles for boolean values, getting the current value from the loaded JSON
                st.toggle('Fuel Consumption', value=hardmode_options.get('fuel', False), key="hardmode_fuel")
                st.toggle('Terrain Deformation', value=hardmode_options.get('convoyTerrainDeformationEnable', False), key="hardmode_terrain")
                st.toggle('Realistic Convoys', value=hardmode_options.get('realisticConvoys', False), key="hardmode_convoys")
                st.toggle('Manual Gearbox', value=hardmode_options.get('gearbox', False), key="hardmode_gearbox")

            with hm_col2:
                st.markdown("##### Difficulty Tiers (0=Easiest)")
                # Create sliders for numeric values, getting the current value from the loaded JSON
                st.slider('Fuel Cost', 1, 3, value=hardmode_options.get('fuelCost', 0), key="hardmode_fuelCost")
                st.slider('Quarry Zone', 1, 4, value=hardmode_options.get('quarryZones', 0), key="hardmode_quarryZones")
                st.slider('Bridge Cost', 1, 3, value=hardmode_options.get('bridges', 0), key="hardmode_bridges")
                st.slider('Vehicle Cost', 1, 4, value=hardmode_options.get('vehicleCost', 0), key="hardmode_vehicleCost")
                st.slider('Economy Modifiers (Objective Reward)', 1, 3, value=hardmode_options.get('objectiveReward', 0), key="hardmode_objectiveReward")
                st.slider('Recovery Rules', 0, 5, value=hardmode_options.get('recovery', 0), key="hardmode_recovery")
        else:
            # If the section doesn't exist, show a warning and a checkbox to create it
            st.warning("This save file does not have a `hardmodeOptions` section.")
            if st.checkbox("Enable and Edit Hard Mode Settings"):
                # Define the default (easy) settings
                default_options = {
                    "fuel": False, "convoyTerrainDeformationEnable": False, "realisticConvoys": False,
                    "gearbox": False, "fuelCost": 0, "quarryZones": 0, "bridges": 0,
                    "vehicleCost": 0, "objectiveReward": 0, "recovery": 0
                }
                # Add the default section to the JSON data in the session state
                st.session_state.json_data["SslValue"]["hardmodeOptions"] = default_options
                st.success("Hard Mode section has been added! The options are now visible above.")
                # Rerun the script to immediately show the new editing UI
                st.rerun()

        st.markdown("---") # Visual separator before the save button
        # =================================================================
        # END: NEW CODE BLOCK for Hard Mode UI
        # =================================================================



    # --- Save Button Logic ---
    if st.button("Save Changes to New File", help="Click to apply changes and download the new save file."):
        if st.session_state.json_data and st.session_state.original_file_content_bytes:
            # Create a deep copy of the JSON data to modify, avoiding direct modification of session_state.json_data
            # until the very end, to prevent unexpected Streamlit rerender issues or stale state.
            modified_json_data = json.loads(json.dumps(st.session_state.json_data)) 
            ssl_value_to_modify = modified_json_data.get('SslValue', {})
            if not ssl_value_to_modify:
                modified_json_data['SslValue'] = {}
                ssl_value_to_modify = modified_json_data['SslValue']

            # Apply changes only if values differ from initial_values
            if xp_value != st.session_state.initial_values['xp']:
                ssl_value_to_modify['xp'] = xp_value

            if cash_value != st.session_state.initial_values['money']:
                ssl_value_to_modify['money'] = cash_value
            
            # Apply Company Name change
            if company_name_value != st.session_state.initial_values['companyName']:
                ssl_value_to_modify['companyName'] = company_name_value


            # --- Apply Recovery Coins change using ALL_LEVELS_LIST ---
            if recovery_coins_value != st.session_state.initial_values['recovery_coins']:
                if 'recoveryCoins' not in ssl_value_to_modify:
                    ssl_value_to_modify['recoveryCoins'] = {}
                for map_name in ALL_LEVELS_LIST: # Iterate through all known levels
                    ssl_value_to_modify['recoveryCoins'][map_name] = recovery_coins_value


             # --- Apply Unlock All Levels change (updated logic) ---
            if unlock_levels: # If checkbox is currently checked
                ssl_value_to_modify["unlockedLevels"] = ALL_LEVELS_LIST
            # # Only delete if it was initially fully unlocked and now explicitly unchecked
            # elif not unlock_levels and st.session_state.initial_unlocked_levels_checkbox_state:
            #     if 'unlockedLevels' in ssl_value_to_modify: # Ensure it exists before deleting
            #         del ssl_value_to_modify['unlockedLevels']
            # ELSE (if not unlock_levels AND not initial_unlocked_levels_checkbox_state):
            # The user did nothing, and it wasn't fully unlocked initially.
            # So, the 'unlockedLevels' entry remains exactly as it was loaded.

            # --- Apply Unlock All Trucks change (updated logic) ---
            if unlock_trucks: # If checkbox is currently checked
                ssl_value_to_modify["newUnlockedTrucks"] = ALL_TRUCKS_LIST
                ssl_value_to_modify['lockedTrucks'] = [] # Set it to an empty list
            
            # --- Apply Remove Rusty Trucks change ---
            if remove_rusty_trucks:
                if 'storedTrucks' in ssl_value_to_modify:
                    for truck_name in list(ssl_value_to_modify['storedTrucks'].keys()): # Iterate over a copy to allow modification
                        if truck_name.endswith("_old") and truck_name != "khan_lo_strannik_mob_old": # Added exception
                            ssl_value_to_modify['storedTrucks'][truck_name] = [] # Set to empty list

            # # --- Apply Lift All Fog of War change ---
            # if lift_fog:
            #     if 'fogOfWarProgress' not in ssl_value_to_modify:
            #         ssl_value_to_modify['fogOfWarProgress'] = {}
            #     for map_name in ALL_LEVELS_LIST: # Use ALL_LEVELS_LIST as a reference for map names
            #         ssl_value_to_modify['fogOfWarProgress'][map_name] = 100.0

            # --- Resources (Logs, Steel Beams, Concrete, Steel Pipes) using ALL_LEVELS_LIST ---
            resource_updates_map = { # Maps initial_key to (current_value, index)
                'logs_4_idx': (logs_value, 4),
                'steel_beams_5_idx': (steel_beams_value, 5),
                'concrete_6_idx': (concrete_value, 6),
                'steel_pipes_7_idx': (steel_pipes_value, 7)
            }

            if 'fobsResources' not in ssl_value_to_modify:
                ssl_value_to_modify['fobsResources'] = {}

            for map_name in ALL_LEVELS_LIST: # Iterate through all known levels
                # Ensure the map entry exists in fobsResources
                if map_name not in ssl_value_to_modify['fobsResources']:
                    ssl_value_to_modify['fobsResources'][map_name] = {"resources": [0]*8} # Initialize with 8 zeros if not present

                resources = ssl_value_to_modify['fobsResources'][map_name]['resources']
                for initial_key, (current_val, idx) in resource_updates_map.items():
                    if current_val != st.session_state.initial_values[initial_key]:
                        # Ensure list is long enough, extend with zeros if needed
                        while len(resources) <= idx:
                            resources.append(0)
                        resources[idx] = current_val

            # =================================================================
            # START: NEW CODE BLOCK for Applying Hard Mode Changes
            # =================================================================
            # Check if hardmode_options exists in the data before trying to save
            if "hardmodeOptions" in ssl_value_to_modify:
                # Update the dictionary with the values from the session state of our new widgets
                ssl_value_to_modify["hardmodeOptions"]["fuel"] = st.session_state.hardmode_fuel
                ssl_value_to_modify["hardmodeOptions"]["convoyTerrainDeformationEnable"] = st.session_state.hardmode_terrain
                ssl_value_to_modify["hardmodeOptions"]["realisticConvoys"] = st.session_state.hardmode_convoys
                ssl_value_to_modify["hardmodeOptions"]["gearbox"] = st.session_state.hardmode_gearbox
                ssl_value_to_modify["hardmodeOptions"]["fuelCost"] = st.session_state.hardmode_fuelCost
                ssl_value_to_modify["hardmodeOptions"]["quarryZones"] = st.session_state.hardmode_quarryZones
                ssl_value_to_modify["hardmodeOptions"]["bridges"] = st.session_state.hardmode_bridges
                ssl_value_to_modify["hardmodeOptions"]["vehicleCost"] = st.session_state.hardmode_vehicleCost
                ssl_value_to_modify["hardmodeOptions"]["objectiveReward"] = st.session_state.hardmode_objectiveReward
                ssl_value_to_modify["hardmodeOptions"]["recovery"] = st.session_state.hardmode_recovery
            # =================================================================
            # END: NEW CODE BLOCK for Applying Hard Mode Changes
            # =================================================================

            # Convert modified JSON back to bytes
            decompressed_data_edited = json.dumps(
                modified_json_data,
                indent=3, # Pretty print for readability
                ensure_ascii=False, # Allow non-ASCII characters
                separators=(',', ': ') # Compact separators for smaller output
            ).encode('utf-8')

            # Encode and provide for download
            encode_file(st.session_state.original_file_content_bytes, decompressed_data_edited)
        else:
            st.warning("Please upload a file first to save changes.")

    st.markdown("---")
    # Optional: Display raw JSON for debugging/advanced users
    if st.checkbox("Show Raw JSON (for advanced users)", value=False, help="Displays the full JSON content of the loaded save file."):
        if st.session_state.json_data:
            st.json(st.session_state.json_data)
        else:
            st.info("Upload a file to view raw JSON.")
