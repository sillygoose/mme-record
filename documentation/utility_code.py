# Read and modify the master DID list
        dids = self._load_dids(file='json/did_coverage.json')
        new_dids = []
        for did_record in dids:
            did_id = did_record.get('did_id')
            length = did_record.get('length')
            modules = did_record.get('modules')
            new_dids.append({'did_id': did_id, 'did_id_hex': f"{did_id:04X}", 'length': length, 'modules': modules})
        self._save_dids('json/did_coverage.json', new_dids)
        pass
